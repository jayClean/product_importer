"""Celery application factory for async processing."""

import ssl

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

# Get broker and backend URLs
broker_url = settings.celery_broker_url or settings.redis_url
backend_url = settings.celery_result_url or settings.redis_url

# Convert redis:// to rediss:// for Upstash domains to enable SSL
is_ssl = False
if ".upstash.io" in broker_url and broker_url.startswith("redis://"):
    broker_url = broker_url.replace("redis://", "rediss://", 1)
    is_ssl = True
if ".upstash.io" in backend_url and backend_url.startswith("redis://"):
    backend_url = backend_url.replace("redis://", "rediss://", 1)
    is_ssl = True
# Also check if URL already uses rediss://
if broker_url.startswith("rediss://") or backend_url.startswith("rediss://"):
    is_ssl = True

# Add ssl_cert_reqs to URLs as query parameter (required by Celery Redis backend)
# This ensures the backend sees SSL config during initialization, before config.update()
if is_ssl:
    # Add ssl_cert_reqs=none to both URLs if not already present
    ssl_param = "ssl_cert_reqs=none"
    if "ssl_cert_reqs" not in broker_url:
        separator = "&" if "?" in broker_url else "?"
        broker_url = f"{broker_url}{separator}{ssl_param}"
    if "ssl_cert_reqs" not in backend_url:
        separator = "&" if "?" in backend_url else "?"
        backend_url = f"{backend_url}{separator}{ssl_param}"

# Prepare SSL configuration before creating Celery app
ssl_config = {}
if is_ssl:
    ssl_config = {
        "ssl_cert_reqs": ssl.CERT_NONE,
    }

# Prepare config dict with SSL settings BEFORE creating Celery app
celery_config_dict = {}
if is_ssl:
    ssl_dict = {"ssl_cert_reqs": ssl.CERT_NONE}
    # Set SSL config in the initial config dict
    celery_config_dict.update(
        {
            "result_backend_transport_options": ssl_dict,
            "broker_transport_options": ssl_dict,
            "broker_use_ssl": ssl_dict,
            "result_backend_use_ssl": ssl_dict,
        }
    )

celery_app = Celery(
    "product_importer",
    broker=broker_url,
    backend=backend_url,
)

# Apply SSL config IMMEDIATELY using update() method
# This must happen before ANY operation that might access the backend
if is_ssl:
    ssl_dict = {"ssl_cert_reqs": ssl.CERT_NONE}
    # Update config immediately - this is critical for rediss:// URLs
    celery_app.conf.update(
        {
            "result_backend_transport_options": ssl_dict,
            "broker_transport_options": ssl_dict,
            "broker_use_ssl": ssl_dict,
            "result_backend_use_ssl": ssl_dict,
        }
    )

# Autodiscover tasks from the workers.tasks package
celery_app.autodiscover_tasks(["app.workers.tasks"])

# Explicitly import tasks to ensure they're registered with celery_app
# Tasks use @celery_app.task decorator, so they're automatically registered
from app.workers.tasks import import_products, webhook_test  # noqa: F401

# Task routing by queue - routes tasks to specific queues
celery_app.conf.task_routes = {
    "app.workers.tasks.import_products": {"queue": "imports"},
    "app.workers.tasks.webhook_test": {"queue": "webhooks"},
}
# Set default queue (fallback if routing doesn't match)
celery_app.conf.task_default_queue = "imports"

# Performance and reliability settings
# Optimized for low-memory environments (Railway free tier)
celery_config = {
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "task_acks_late": True,  # Acknowledge after task completion
    "task_reject_on_worker_lost": True,  # Re-queue if worker dies
    "worker_prefetch_multiplier": 1,  # Fair task distribution
    "task_time_limit": 3600,  # 1 hour hard limit
    "task_soft_time_limit": 3300,  # 55 min soft limit
    "result_expires": 3600,  # Results expire after 1 hour
    "broker_connection_retry_on_startup": True,
    # Suppress superuser warnings for containerized environments
    "worker_disable_rate_limits": False,
    "worker_hijack_root_logger": False,
    # Memory optimization settings
    # Note: solo pool doesn't fork, so max_memory_per_child doesn't apply
    # Memory limits are enforced via task-level monitoring
    "worker_max_memory_per_child": 500000,  # 500MB per child (for prefork pool if used later)
    "result_backend_always_retry": True,
    "result_backend_max_retries": 3,
    # Reduce memory usage
    "task_ignore_result": False,  # Keep results but expire quickly
}

# Add SSL config to main config if not already set
if is_ssl:
    ssl_dict = {"ssl_cert_reqs": ssl.CERT_NONE}
    celery_config["broker_use_ssl"] = ssl_dict
    celery_config["result_backend_use_ssl"] = ssl_dict
    celery_config["broker_transport_options"] = ssl_dict.copy()
    celery_config["result_backend_transport_options"] = ssl_dict.copy()

celery_app.conf.update(celery_config)
