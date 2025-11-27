"""Endpoints for CSV upload orchestration and tracking."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies.db import get_session
from app.api.routers.job_helpers import serialize_job
from app.api.schemas.job import JobStatus
from app.db.models.import_job import ImportJob
from app.services.progress_tracker import fetch_progress, publish_progress
from app.storage.file_storage import (
    delete_file_from_redis,
    store_file_in_redis,
)
from app.storage.s3_client import delete_upload, save_upload
from app.workers.tasks.import_products import import_products_task

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    summary="Start a CSV import job",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobStatus,
)
async def enqueue_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
) -> JobStatus:
    """Accept CSV file metadata, persist temp storage, and return async job id."""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required",
            )
        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV uploads are supported",
            )

        # Create import job first to get job_id (needed for Redis storage)
        try:
            job = ImportJob(uploaded_file_path="pending")
            db.add(job)
            db.flush()
        except SQLAlchemyError as exc:
            db.rollback()
            logger.error(f"Database error creating import job: {exc}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create import job",
            ) from exc

        # Stage file (both locally and in Redis for separate instance access)
        staged_path = None
        redis_stored = False
        try:
            # Read file content
            await file.seek(0)
            file_content = await file.read()

            # Try to save locally first (for same-instance deployments)
            try:
                await file.seek(0)
                staged_path = save_upload(file, file.filename)
            except Exception as e:
                logger.warning(f"Failed to save file locally: {e}, will use Redis only")

            # Store in Redis for separate instance access
            from io import BytesIO

            file_obj = BytesIO(file_content)
            redis_stored = store_file_in_redis(file_obj, str(job.id))

            # Update job with file path info
            if staged_path:
                absolute_path = (
                    str(staged_path.resolve())
                    if isinstance(staged_path, Path)
                    else str(Path(staged_path).resolve())
                )
                job.uploaded_file_path = absolute_path
            elif redis_stored:
                # File is in Redis, store indicator
                job.uploaded_file_path = f"redis:{job.id}"
            else:
                # Both failed
                raise ValueError("Failed to stage file both locally and in Redis")

            db.flush()
        except ValueError as exc:
            # Clean up job if file staging failed
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File staging failed: {str(exc)}",
            ) from exc
        except OSError as exc:
            logger.error(f"OS error staging file: {exc}", exc_info=True)
            db.rollback()
            # Clean up Redis entry if created
            if redis_stored:
                try:
                    delete_file_from_redis(str(job.id))
                except Exception:
                    pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded file",
            ) from exc
        except Exception as exc:
            logger.error(f"Unexpected error staging file: {exc}", exc_info=True)
            db.rollback()
            # Clean up Redis entry if created
            if redis_stored:
                try:
                    delete_file_from_redis(str(job.id))
                except Exception:
                    pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the file",
            ) from exc

        # Publish initial progress and enqueue task
        try:
            publish_progress(job.id, 0.0, "Queued", status="pending", meta={})
            # Pass the file path (or Redis indicator) to the task
            file_path_for_task = str(staged_path) if staged_path else f"redis:{job.id}"
            # Explicitly send to imports queue to ensure routing works
            import_products_task.apply_async(
                args=(job.id, file_path_for_task),
                queue="imports",
            )
        except Exception as exc:
            logger.error(f"Error enqueueing import task: {exc}", exc_info=True)
            # Job is created but task failed to enqueue - mark as failed
            job.status = "failed"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to start import process",
            ) from exc

        logger.info(f"Created import job {job.id} for file {file.filename}")
        return serialize_job(
            job, progress_payload={"progress": 0.0, "status": "pending"}
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error in enqueue_import: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from exc


@router.get(
    "/{job_id}/status",
    summary="Check import progress",
    response_model=JobStatus,
)
async def get_import_status(
    job_id: str,
    db: Session = Depends(get_session),
) -> JobStatus:
    """Expose latest processing stats to power UI progress bars (SSE/polling)."""
    try:
        job = db.get(ImportJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        try:
            progress_payload = fetch_progress(job_id)
        except Exception as exc:
            logger.warning(
                f"Failed to fetch progress from Redis for job {job_id}: {exc}"
            )
            progress_payload = {}

        return serialize_job(job, progress_payload=progress_payload)

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.error(
            f"Database error fetching job status {job_id}: {exc}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status",
        ) from exc
    except Exception as exc:
        logger.error(
            f"Unexpected error fetching job status {job_id}: {exc}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from exc
