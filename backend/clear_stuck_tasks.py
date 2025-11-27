#!/usr/bin/env python3
"""Script to clear stuck tasks from the default celery queue."""

from app.core.config import get_settings
from redis import Redis
import ssl
from urllib.parse import urlparse

settings = get_settings()
redis_url = settings.celery_broker_url or settings.redis_url

print("Connecting to Redis...")
parsed = urlparse(redis_url)

if redis_url.startswith("rediss://"):
    redis_client = Redis(
        host=parsed.hostname,
        port=parsed.port or 6379,
        password=parsed.password,
        ssl=True,
        ssl_cert_reqs=ssl.CERT_NONE,
        decode_responses=False
    )
else:
    redis_client = Redis.from_url(redis_url, decode_responses=False)

# Check celery queue
celery_queue_length = redis_client.llen("celery")
print(f"\nTasks in 'celery' queue: {celery_queue_length}")

if celery_queue_length > 0:
    response = input(f"\nDo you want to clear {celery_queue_length} tasks from 'celery' queue? (yes/no): ")
    if response.lower() == "yes":
        redis_client.delete("celery")
        print("✓ Cleared 'celery' queue")
    else:
        print("Cancelled. Tasks remain in queue.")
else:
    print("✓ No tasks in 'celery' queue")

# Check imports queue
imports_queue_length = redis_client.llen("imports")
print(f"\nTasks in 'imports' queue: {imports_queue_length}")

# Check webhooks queue
webhooks_queue_length = redis_client.llen("webhooks")
print(f"Tasks in 'webhooks' queue: {webhooks_queue_length}")

print("\nDone!")

