"""Shared helpers for publishing job progress to Redis/SSE."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.utils.redis_client import create_redis_client

settings = get_settings()
redis_client = create_redis_client(settings.redis_url, decode_responses=True)
PROGRESS_PREFIX = "jobs:progress:"
PROGRESS_TTL = timedelta(hours=24)


def _key(job_id: str) -> str:
    return f"{PROGRESS_PREFIX}{job_id}"


def publish_progress(
    job_id: str,
    progress: float,
    message: str | None = None,
    *,
    status: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    """Persist progress snapshots so UI can subscribe."""
    payload = {
        "job_id": job_id,
        "progress": max(0.0, min(progress, 1.0)),
        "message": message,
        "status": status,
        "meta": meta or {},
    }
    try:
        redis_client.set(
            _key(job_id),
            json.dumps(payload),
            ex=int(PROGRESS_TTL.total_seconds()),
        )
    except RedisError:
        # Redis availability should not break ingestion.
        pass


def fetch_progress(job_id: str) -> dict[str, Any]:
    """Return latest job telemetry used by the jobs endpoint."""
    try:
        raw = redis_client.get(_key(job_id))
    except RedisError:
        return {}
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
