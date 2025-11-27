"""File storage abstraction that supports both local filesystem and Redis for separate instances."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import BinaryIO

from redis.exceptions import RedisError

from app.core.config import get_settings
from app.services.progress_tracker import redis_client
from app.storage.s3_client import save_upload

logger = logging.getLogger(__name__)

settings = get_settings()

# Redis key prefix for file storage
FILE_STORAGE_PREFIX = "files:upload:"
# TTL for files in Redis (24 hours)
FILE_STORAGE_TTL = 86400  # seconds


def store_file_in_redis(file_obj: BinaryIO, job_id: str) -> bool:
    """Store file content in Redis for worker access across separate instances.

    Args:
        file_obj: File-like object to read from
        job_id: Job ID to use as Redis key

    Returns:
        True if successfully stored, False otherwise
    """
    try:
        file_obj.seek(0)
        file_content = file_obj.read()

        # Check file size (Redis has limits, Upstash free tier ~256MB)
        max_size = 100 * 1024 * 1024  # 100MB limit for Redis storage
        if len(file_content) > max_size:
            logger.warning(
                f"File too large for Redis storage ({len(file_content)} bytes), "
                f"will use local filesystem fallback"
            )
            return False

        # We need binary storage, so create a client without decode_responses
        from app.utils.redis_client import create_redis_client

        binary_redis = create_redis_client(settings.redis_url, decode_responses=False)

        key = f"{FILE_STORAGE_PREFIX}{job_id}"
        binary_redis.set(key, file_content, ex=FILE_STORAGE_TTL)
        binary_redis.close()

        logger.info(
            f"Stored file in Redis for job {job_id} ({len(file_content)} bytes)"
        )
        return True
    except RedisError as e:
        logger.warning(f"Failed to store file in Redis: {e}, will use local filesystem")
        return False
    except Exception as e:
        logger.error(f"Unexpected error storing file in Redis: {e}", exc_info=True)
        return False


def get_file_from_redis(job_id: str) -> bytes | None:
    """Retrieve file content from Redis.

    Args:
        job_id: Job ID used as Redis key

    Returns:
        File content as bytes, or None if not found
    """
    try:
        from app.utils.redis_client import create_redis_client

        binary_redis = create_redis_client(settings.redis_url, decode_responses=False)

        key = f"{FILE_STORAGE_PREFIX}{job_id}"
        content = binary_redis.get(key)
        binary_redis.close()

        if content:
            logger.info(
                f"Retrieved file from Redis for job {job_id} ({len(content)} bytes)"
            )
        return content
    except RedisError as e:
        logger.warning(f"Failed to retrieve file from Redis: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving file from Redis: {e}", exc_info=True)
        return None


def save_file_to_temp(
    file_content: bytes, job_id: str, original_name: str | None = None
) -> Path:
    """Save file content to temporary local file (for worker processing).

    Args:
        file_content: File content as bytes
        job_id: Job ID for filename
        original_name: Original filename (for extension)

    Returns:
        Path to saved file
    """
    from app.core.config import get_settings
    from pathlib import Path

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir).resolve()
    uploads_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(original_name or "upload.csv").suffix or ".csv"
    target_name = f"{job_id}{suffix}"
    target_path = uploads_dir / target_name

    target_path.write_bytes(file_content)
    logger.info(f"Saved file to temporary location: {target_path}")

    return target_path


def delete_file_from_redis(job_id: str) -> None:
    """Delete file from Redis storage.

    Args:
        job_id: Job ID used as Redis key
    """
    try:
        from app.utils.redis_client import create_redis_client

        binary_redis = create_redis_client(settings.redis_url, decode_responses=False)

        key = f"{FILE_STORAGE_PREFIX}{job_id}"
        binary_redis.delete(key)
        binary_redis.close()

        logger.info(f"Deleted file from Redis for job {job_id}")
    except Exception as e:
        logger.warning(f"Failed to delete file from Redis: {e}")


def stage_file_with_redis(
    upload_file: BinaryIO, job_id: str, original_name: str | None = None
) -> tuple[Path | None, bool]:
    """Stage file for processing, storing in Redis for cross-instance access.

    This function:
    1. Tries to store file in Redis (for separate instances)
    2. Falls back to local filesystem if Redis fails or file too large
    3. Returns both the local path (if saved) and whether Redis storage succeeded

    Args:
        upload_file: File-like object
        job_id: Job ID
        original_name: Original filename

    Returns:
        Tuple of (local_path or None, redis_stored: bool)
    """
    # Always try to save locally first (for same-instance deployments)
    local_path = None
    try:
        local_path = save_upload(upload_file, original_name)
    except Exception as e:
        logger.warning(f"Failed to save file locally: {e}")

    # Try to store in Redis for separate instance access
    upload_file.seek(0)  # Reset for Redis storage
    redis_stored = store_file_in_redis(upload_file, job_id)

    return local_path, redis_stored
