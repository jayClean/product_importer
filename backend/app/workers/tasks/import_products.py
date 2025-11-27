"""Celery task for long-running CSV ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.db.models.import_job import ImportJob
from app.db.session import SessionLocal
from app.services import csv_ingest
from app.services.progress_tracker import publish_progress
from app.utils.memory_monitor import (
    check_memory_exceeded,
    force_gc,
    log_memory_status,
)
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, name="app.workers.tasks.import_products")
def import_products_task(self, job_id: str, file_path: str):
    """Process CSV chunks, upsert rows, and update progress tracker."""
    session = SessionLocal()
    job: ImportJob | None = session.get(ImportJob, job_id)
    if not job:
        session.close()
        return

    # Resolve to absolute path to ensure consistency across processes
    path_obj = Path(file_path).resolve()
    if not path_obj.exists():
        raise FileNotFoundError(
            f"CSV file not found: {path_obj}. Current working directory: {Path.cwd()}"
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
        session.close()
