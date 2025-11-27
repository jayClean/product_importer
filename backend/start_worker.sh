#!/bin/bash
# Start script for Celery worker (separate instance)
# Use this when deploying worker as a separate service

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

# Set memory-efficient Python options
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Memory limits (defaults: 500MB baseline, 800MB hard limit)
# Can be overridden via environment variables in your deployment platform
export CELERY_MEMORY_BASELINE="${CELERY_MEMORY_BASELINE:-500M}"
export CELERY_MEMORY_LIMIT="${CELERY_MEMORY_LIMIT:-800M}"

echo "Memory limits: baseline=${CELERY_MEMORY_BASELINE}, limit=${CELERY_MEMORY_LIMIT}"

# Start Celery worker
# Use solo pool for Railway (simpler, less resource intensive, no fork issues)
# --without-mingle and --without-gossip avoid superuser privilege warnings
# Solo pool is single-threaded, perfect for Railway's resource constraints
# Reduced log level to warning to save memory
echo "Starting Celery worker..."

# Suppress superuser warning using Python's warning filter
# Railway containers run as root, which is safe in containerized environments
PYTHONWARNINGS="ignore::UserWarning:celery.platforms" \
exec celery -A app.workers.celery_app.celery_app worker \
    --loglevel=warning \
    --queues=imports,webhooks,celery \
    --pool=solo \
    --without-mingle \
    --without-gossip \
    --max-tasks-per-child=50
