"""Shared helpers for shaping job responses."""
from __future__ import annotations

from app.api.schemas.job import JobStatus
from app.db.models.import_job import ImportJob


def serialize_job(job: ImportJob, progress_payload: dict | None) -> JobStatus:
    """Combine DB state + cached progress snapshot into a response schema."""
    progress_payload = progress_payload or {}

    calculated_progress = progress_payload.get("progress")
    if calculated_progress is None and job.total_rows:
        calculated_progress = job.processed_rows / job.total_rows

    message = progress_payload.get("message")
    if not message:
        total_display = job.total_rows if job.total_rows else "?"
        message = f"Processed {job.processed_rows}/{total_display} rows"

    status_value = progress_payload.get("status") or job.status

    return JobStatus(
        id=job.id,
        type="import_products",
        status=status_value,
        progress=calculated_progress,
        message=message,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        error_message=job.error_message,
        started_at=job.started_at or job.created_at,
        finished_at=job.finished_at,
        meta=progress_payload.get("meta") or job.meta or {},
    )

