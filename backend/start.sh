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

# Start Celery worker in background
celery -A app.workers.celery_app.celery_app worker \
    --loglevel=info \
    --queues=imports,webhooks,celery \
    --detach \
    --pidfile=/tmp/celery.pid \
    --logfile=/tmp/celery.log

# Start FastAPI server (foreground - this keeps the service alive)
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}

