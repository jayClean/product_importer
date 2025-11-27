"""Simple health and readiness endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import engine
from app.utils.redis_client import create_redis_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", summary="Liveness probe")
async def live() -> dict[str, str]:
    """Indicates API process is running.

    Used by orchestration systems (Kubernetes, Docker, etc.) to determine
    if the container/process should be restarted.
    """
    return {"status": "ok", "service": "product-importer-api"}


@router.get("/cors-config", summary="CORS configuration debug endpoint")
async def cors_config() -> dict[str, Any]:
    """Debug endpoint to check CORS configuration."""
    settings = get_settings()
    return {
        "cors_origins_raw": settings.cors_origins_raw,
        "cors_origins_parsed": settings.cors_origins,
        "note": "Set CORS_ORIGINS environment variable on Render to allow your frontend origin",
    }


@router.get("/ready", summary="Readiness probe")
async def ready() -> dict[str, Any]:
    """Check readiness of dependencies (database, Redis, Celery).

    Returns detailed status of all critical dependencies:
    - Database connectivity
    - Redis connectivity
    - Celery broker connectivity (optional check)

    Used by load balancers to determine if traffic should be routed to this instance.
    """
    checks: dict[str, Any] = {
        "status": "ok",
        "service": "product-importer-api",
        "checks": {},
    }
    all_healthy = True

    # Check database connectivity
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        checks["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful",
        }
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        checks["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
        }
        all_healthy = False
    except Exception as e:
        logger.error(f"Unexpected error in database health check: {e}", exc_info=True)
        checks["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Unexpected error: {str(e)}",
        }
        all_healthy = False

    # Check Redis connectivity
    try:
        settings = get_settings()
        redis_client = create_redis_client(
            settings.redis_url, decode_responses=True, socket_connect_timeout=2
        )
        redis_client.ping()
        checks["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful",
        }
        redis_client.close()
    except RedisError as e:
        logger.error(f"Redis health check failed: {e}", exc_info=True)
        checks["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}",
        }
        all_healthy = False
    except Exception as e:
        logger.error(f"Unexpected error in Redis health check: {e}", exc_info=True)
        checks["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Unexpected error: {str(e)}",
        }
        all_healthy = False

    # Check Celery broker (optional, uses same Redis)
    try:
        settings = get_settings()
        broker_url = settings.celery_broker_url or settings.redis_url
        celery_redis = create_redis_client(
            broker_url, decode_responses=True, socket_connect_timeout=2
        )
        celery_redis.ping()
        checks["checks"]["celery_broker"] = {
            "status": "healthy",
            "message": "Celery broker connection successful",
        }
        celery_redis.close()
    except Exception as e:
        logger.warning(f"Celery broker health check failed: {e}", exc_info=True)
        checks["checks"]["celery_broker"] = {
            "status": "unhealthy",
            "message": f"Celery broker connection failed: {str(e)}",
        }
        # Don't fail readiness for Celery broker issues (worker might be separate)

    if not all_healthy:
        checks["status"] = "unhealthy"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=checks,
        )

    return checks
