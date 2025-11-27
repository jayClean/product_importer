"""Celery task for long-running CSV ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.db.models.import_job import ImportJob
from app.db.session import SessionLocal
from app.services import csv_ingest
from app.services.progress_tracker import publish_progress
from app.storage.file_storage import (
    delete_file_from_redis,
    get_file_from_redis,
    save_file_to_temp,
)
from app.utils.memory_monitor import (
    check_memory_exceeded,
    force_gc,
    log_memory_status,
)
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="app.workers.tasks.import_products")
def import_products_task(self, job_id: str, file_path: str):
    """Process CSV chunks, upsert rows, and update progress tracker."""
    import logging

    logger = logging.getLogger(__name__)
    session = SessionLocal()
    job: ImportJob | None = session.get(ImportJob, job_id)
    if not job:
        session.close()
        return

    # Handle file retrieval for separate instances
    # Check if file is stored in Redis (for separate instance deployments)
    temp_file_path: Path | None = None
    path_obj: Path | None = None

    if file_path.startswith("redis:") or job.uploaded_file_path.startswith("redis:"):
        # File is in Redis, retrieve it
        logger.info(f"Retrieving file from Redis for job {job_id}")
        file_content = get_file_from_redis(job_id)
        if not file_content:
            raise FileNotFoundError(
                f"File not found in Redis for job {job_id}. "
                "File may have expired or Redis storage failed."
            )
        # Save to temporary local file for processing
        temp_file_path = save_file_to_temp(file_content, job_id, "upload.csv")
        path_obj = temp_file_path
        logger.info(f"Saved file from Redis to temporary location: {path_obj}")
    else:
        # File is on local filesystem (same instance deployment)
        path_obj = Path(file_path).resolve()
        if not path_obj.exists():
            # Try to get from Redis as fallback
            logger.warning(
                f"Local file not found: {path_obj}, trying Redis fallback for job {job_id}"
            )
            file_content = get_file_from_redis(job_id)
            if file_content:
                temp_file_path = save_file_to_temp(file_content, job_id, "upload.csv")
                path_obj = temp_file_path
                logger.info(f"Retrieved file from Redis fallback: {path_obj}")
            else:
                raise FileNotFoundError(
                    f"CSV file not found: {path_obj}. "
                    f"Current working directory: {Path.cwd()}. "
                    f"Also checked Redis for job {job_id} but not found."
                )
    processed = 0
    inserted_total = 0
    updated_total = 0
    total_rows = 0

    try:
        # Log initial memory status
        log_memory_status("Task start")

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        session.commit()

        total_rows = csv_ingest.count_rows(path_obj)
        job.total_rows = total_rows
        session.commit()

        log_memory_status(f"After counting {total_rows} rows")

        chunk_count = 0
        for chunk in csv_ingest.iter_csv_chunks(path_obj):
            # Check memory before processing chunk
            is_exceeded, current, limit = check_memory_exceeded()
            if is_exceeded:
                error_msg = (
                    f"Memory limit exceeded: {current / 1024 / 1024:.1f}MB >= "
                    f"{limit / 1024 / 1024:.1f}MB. Cannot continue processing."
                )
                logger.error(error_msg)
                raise MemoryError(error_msg)

            # Process chunk
            stats = csv_ingest.upsert_products(chunk, session)
            inserted_total += stats["inserted"]
            updated_total += stats["updated"]
            processed += len(chunk)
            job.processed_rows = processed
            session.commit()

            chunk_count += 1

            # Force garbage collection every 5 chunks to prevent memory buildup
            if chunk_count % 5 == 0:
                force_gc()
                log_memory_status(f"After {chunk_count} chunks, {processed} rows")

            progress_value = processed / total_rows if total_rows else 0.0
            publish_progress(
                job_id,
                progress_value,
                message=f"Processed {processed}/{total_rows} rows",
                status="running",
                meta={
                    "processed": processed,
                    "total": total_rows,
                    "inserted": inserted_total,
                    "updated": updated_total,
                },
            )

        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        session.commit()

        # Final garbage collection and memory log
        force_gc()
        log_memory_status("Task complete")

        publish_progress(
            job_id,
            1.0,
            message="Import complete",
            status="completed",
            meta={
                "processed": processed,
                "total": total_rows,
                "inserted": inserted_total,
                "updated": updated_total,
            },
        )
    except MemoryError as exc:
        # Special handling for memory errors
        session.rollback()
        job.status = "failed"
        job.error_message = f"Out of memory: {str(exc)}"
        job.finished_at = datetime.now(timezone.utc)
        session.commit()

        log_memory_status("Task failed (OOM)")
        force_gc()  # Try to free memory before failing

        progress_value = processed / total_rows if total_rows else 0.0
        publish_progress(
            job_id,
            progress_value,
            message="Import failed: Out of memory",
            status="failed",
            meta={
                "processed": processed,
                "total": total_rows,
                "inserted": inserted_total,
                "updated": updated_total,
                "error": str(exc),
                "error_type": "MemoryError",
            },
        )
        raise
    except Exception as exc:  # pragma: no cover
        session.rollback()
        job.status = "failed"
        job.error_message = str(exc)
        job.finished_at = datetime.now(timezone.utc)
        session.commit()

        log_memory_status("Task failed")
        force_gc()

        progress_value = processed / total_rows if total_rows else 0.0
        publish_progress(
            job_id,
            progress_value,
            message="Import failed",
            status="failed",
            meta={
                "processed": processed,
                "total": total_rows,
                "inserted": inserted_total,
                "updated": updated_total,
                "error": str(exc),
            },
        )
        raise
    finally:
        # Cleanup: delete temporary file and Redis entry
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {e}")

        # Delete from Redis if it was stored there
        try:
            delete_file_from_redis(job_id)
        except Exception as e:
            logger.warning(f"Failed to delete file from Redis: {e}")

        session.close()
