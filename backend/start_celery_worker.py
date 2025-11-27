#!/usr/bin/env python3
"""Start Celery worker with suppressed security warnings for containerized environments."""

import warnings
import sys
from celery.bin import worker

# Suppress the superuser privilege warning
warnings.filterwarnings('ignore', category=UserWarning, message='.*superuser privileges.*')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*superuser privileges.*')

# Import the Celery app
from app.workers.celery_app import celery_app

if __name__ == '__main__':
    # Create worker command
    worker_app = worker.worker(app=celery_app)
    
    # Set up arguments
    sys.argv = [
        'celery',
        '-A', 'app.workers.celery_app.celery_app',
        'worker',
        '--loglevel=info',
        '--queues=imports,webhooks,celery',
        '--pool=solo',
        '--without-mingle',
        '--without-gossip',
    ] + sys.argv[1:]
    
    # Run the worker
    worker_app.run()

