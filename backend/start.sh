#!/bin/bash
# Start script for Railway/Render that runs both API and Celery worker in the same service
# This allows them to share the filesystem for uploaded files

set -e

# Change to backend directory
cd "$(dirname "$0")"

# Get absolute path to backend directory
BACKEND_DIR="$(pwd)"
UPLOADS_DIR="${UPLOADS_DIR:-${BACKEND_DIR}/storage/uploads}"

# Ensure uploads directory exists with absolute path
mkdir -p "$UPLOADS_DIR"
echo "Using uploads directory: $UPLOADS_DIR"

# Export UPLOADS_DIR so Python code can use it
export UPLOADS_DIR="$UPLOADS_DIR"

# Function to cleanup Celery on exit
cleanup() {
    echo "Shutting down Celery worker..."
    if [ -f /tmp/celery.pid ]; then
        kill $(cat /tmp/celery.pid) 2>/dev/null || true
        rm -f /tmp/celery.pid
    fi
    exit 0
}

# Trap signals to cleanup
trap cleanup SIGTERM SIGINT

# Start Celery worker in background
# Use solo pool for Railway (simpler, less resource intensive, no fork issues)
# --without-mingle and --without-gossip avoid superuser privilege warnings
# Solo pool is single-threaded, perfect for Railway's resource constraints
# Reduced log level to warning to save memory
echo "Starting Celery worker..."
# Suppress superuser warning using Python's warning filter
# Railway containers run as root, which is safe in containerized environments
# Set memory-efficient Python options
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
PYTHONWARNINGS="ignore::UserWarning:celery.platforms" \
celery -A app.workers.celery_app.celery_app worker \
    --loglevel=warning \
    --queues=imports,webhooks,celery \
    --pool=solo \
    --without-mingle \
    --without-gossip \
    --max-tasks-per-child=50 \
    --detach \
    --pidfile=/tmp/celery.pid \
    --logfile=/tmp/celery.log

# Wait a moment to ensure Celery started
sleep 3

# Check if Celery is running
if [ -f /tmp/celery.pid ]; then
    CELERY_PID=$(cat /tmp/celery.pid)
    if kill -0 "$CELERY_PID" 2>/dev/null; then
        echo "✓ Celery worker started successfully (PID: $CELERY_PID)"
    else
        echo "✗ Celery worker process not running. PID file exists but process is dead."
        echo "Last 30 lines of Celery log:"
        tail -30 /tmp/celery.log 2>/dev/null || echo "No log file found"
        echo "Attempting to start Celery without detach to see errors..."
        # Try starting without detach to see what's wrong (will run in background via &)
        PYTHONWARNINGS="ignore::UserWarning:celery.platforms" \
        celery -A app.workers.celery_app.celery_app worker \
            --loglevel=info \
            --queues=imports,webhooks,celery \
            --pool=solo \
            --without-mingle \
            --without-gossip \
            --logfile=/tmp/celery.log &
        echo $! > /tmp/celery.pid
        sleep 2
    fi
else
    echo "✗ Celery PID file not found. Worker may have failed to start."
    echo "Checking for any Celery processes..."
    ps aux | grep celery | grep -v grep || echo "No Celery processes found"
fi

# Start FastAPI server (foreground - this keeps the service alive)
# Use single worker to reduce memory usage
echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --log-level warning

