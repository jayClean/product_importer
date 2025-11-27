#!/usr/bin/env python3
"""Diagnostic script to check Celery queue configuration and status."""

import sys
from app.workers.celery_app import celery_app
from app.core.config import get_settings

settings = get_settings()

print("=" * 60)
print("Celery Queue Diagnostic")
print("=" * 60)

# Check configuration
print("\n1. Celery Configuration:")
print(f"   Broker URL: {settings.celery_broker_url or settings.redis_url}")
print(f"   Backend URL: {settings.celery_result_url or settings.redis_url}")
print(f"   Default Queue: {celery_app.conf.task_default_queue}")
print(f"   Task Routes: {celery_app.conf.task_routes}")

# Check registered tasks
print("\n2. Registered Tasks:")
try:
    registered = celery_app.tasks.keys()
    for task_name in sorted(registered):
        if "import" in task_name.lower() or "webhook" in task_name.lower():
            task = celery_app.tasks[task_name]
            print(f"   - {task_name}")
            print(f"     Queue: {getattr(task, 'queue', 'default')}")
            print(f"     Routing Key: {getattr(task, 'routing_key', 'N/A')}")
except Exception as e:
    print(f"   Error: {e}")

# Check active workers
print("\n3. Active Workers:")
try:
    inspect = celery_app.control.inspect()
    active_workers = inspect.active_queues()
    if active_workers:
        for worker_name, queues in active_workers.items():
            print(f"   Worker: {worker_name}")
            for queue in queues:
                print(f"     - Queue: {queue.get('name', 'unknown')}")
    else:
        print("   No active workers found")
except Exception as e:
    print(f"   Error checking workers: {e}")

# Check queue lengths in Redis
print("\n4. Queue Lengths (from Redis):")
try:
    from redis import Redis
    from urllib.parse import urlparse
    
    redis_url = settings.celery_broker_url or settings.redis_url
    # Parse Redis URL
    parsed = urlparse(redis_url)
    
    # Handle rediss://
    if redis_url.startswith("rediss://"):
        import ssl
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
    
    # Check common queue names
    queue_names = ["imports", "webhooks", "celery"]  # celery is default
    for queue_name in queue_names:
        # Celery uses different key formats
        keys_to_check = [
            queue_name,  # Direct queue name
            f"celery",  # Default queue
            f"_kombu.binding.{queue_name}",  # Kombu binding
        ]
        for key in keys_to_check:
            try:
                length = redis_client.llen(key)
                if length > 0:
                    print(f"   {key}: {length} items")
            except:
                pass
    
    # List all keys to see what's actually there
    print("\n5. All Celery-related keys in Redis:")
    try:
        all_keys = redis_client.keys("*celery*")
        kombu_keys = redis_client.keys("*kombu*")
        import_keys = redis_client.keys("*import*")
        
        for key_list, prefix in [(all_keys, "celery"), (kombu_keys, "kombu"), (import_keys, "import")]:
            if key_list:
                print(f"   {prefix} keys:")
                for key in key_list[:10]:  # Show first 10
                    try:
                        key_str = key.decode() if isinstance(key, bytes) else key
                        key_type = redis_client.type(key).decode() if isinstance(redis_client.type(key), bytes) else redis_client.type(key)
                        if key_type == "list":
                            length = redis_client.llen(key)
                            print(f"     {key_str} ({key_type}): {length} items")
                        else:
                            print(f"     {key_str} ({key_type})")
                    except:
                        pass
    except Exception as e:
        print(f"   Error listing keys: {e}")
        
except Exception as e:
    print(f"   Error connecting to Redis: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Diagnostic Complete")
print("=" * 60)

