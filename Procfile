web: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: cd backend && celery -A app.workers.celery_app.celery_app worker --loglevel=info --queues=imports,webhooks,celery

