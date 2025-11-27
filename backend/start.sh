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
echo "Starting Celery worker..."
celery -A app.workers.celery_app.celery_app worker \
    --loglevel=info \
    --queues=imports,webhooks,celery \
    --pool=solo \
    --without-mingle \
    --without-gossip \
    --detach \
    --pidfile=/tmp/celery.pid \
    --logfile=/tmp/celery.log

# Wait a moment to ensure Celery started
sleep 2

# Check if Celery is running
if [ -f /tmp/celery.pid ] && kill -0 $(cat /tmp/celery.pid) 2>/dev/null; then
    echo "Celery worker started successfully (PID: $(cat /tmp/celery.pid))"
else
    echo "WARNING: Celery worker may not have started correctly. Check logs:"
    tail -20 /tmp/celery.log 2>/dev/null || echo "No log file found"
fi

# Start FastAPI server (foreground - this keeps the service alive)
echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}

