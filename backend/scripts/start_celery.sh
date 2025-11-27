#!/bin/bash
# Start Celery worker for product importer

set -e

# Change to backend directory
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start Celery worker
# Note: Including 'celery' queue temporarily to process old tasks
# Once old tasks are processed, you can remove 'celery' from the queue list
exec celery -A app.workers.celery_app.celery_app worker \
    --loglevel=info \
    --queues=imports,webhooks,celery \
    --concurrency=4

