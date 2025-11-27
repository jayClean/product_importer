"""Async job tracking endpoints (imports, webhook tests, etc.)."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies.db import get_session
from app.api.routers.job_helpers import serialize_job
from app.api.schemas.job import JobStatus
from app.db.models.import_job import ImportJob
from app.services.progress_tracker import fetch_progress

router = APIRouter()


@router.get(
    "/",
    summary="List all import jobs",
    response_model=list[JobStatus],
)
async def list_jobs(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of jobs to return"),
    status: str | None = Query(None, description="Filter by status (pending, running, completed, failed)"),
    db: Session = Depends(get_session),
) -> list[JobStatus]:
    """Return a list of all import jobs, optionally filtered by status.
    
    Jobs are returned in reverse chronological order (newest first).
    Each job includes its latest progress information from Redis.
    """
    try:
        query = select(ImportJob)
        
        if status:
            query = query.where(ImportJob.status == status)
        
        query = query.order_by(ImportJob.created_at.desc()).limit(limit)
        
        jobs = db.scalars(query).all()
        
        # Fetch progress for each job and serialize
        result = []
        for job in jobs:
            progress_payload = fetch_progress(job.id)
            result.append(serialize_job(job, progress_payload))
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve jobs: {str(e)}"
        )


@router.get(
    "/{job_id}",
    summary="Fetch job metadata and latest progress",
    response_model=JobStatus,
)
async def get_job(
    job_id: str,
    db: Session = Depends(get_session),
) -> JobStatus:
    """Expose job state for polling dashboards and audit logs."""
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    progress_payload = fetch_progress(job_id)
    return serialize_job(job, progress_payload)


@router.get(
    "/{job_id}/stream",
    summary="Server-Sent Events stream for real-time progress",
)
async def stream_job_progress(
    job_id: str,
    db: Session = Depends(get_session),
) -> StreamingResponse:
    """Stream job progress updates via Server-Sent Events (SSE).
    
    The client should connect to this endpoint and listen for 'data:' events.
    Each event contains a JSON payload with the latest job status.
    
    Example client usage:
    ```javascript
    const eventSource = new EventSource('/api/jobs/{job_id}/stream');
    eventSource.onmessage = (e) => {
      const data = JSON.parse(e.data);
      console.log('Progress:', data.progress);
    };
    ```
    
    The stream closes automatically when the job completes or fails.
    """
    # Verify job exists before starting stream
    job = db.get(ImportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """Yield SSE-formatted progress updates."""
        last_progress = -1.0
        consecutive_no_change = 0
        
        # Create a new session for the generator to avoid session detachment issues
        # The dependency session closes when the function returns, but the generator continues
        from app.db.session import SessionLocal
        session = SessionLocal()
        
        try:
            while True:
                # Fetch latest progress from Redis
                progress_payload = fetch_progress(job_id)
                
                # Query job fresh from DB to get latest status
                # This avoids session detachment issues with streaming responses
                job = session.get(ImportJob, job_id)
                if not job:
                    yield "event: error\ndata: {\"error\": \"Job not found\"}\n\n"
                    break
                
                # Serialize job status
                job_status = serialize_job(job, progress_payload)
                current_progress = job_status.progress or 0.0
                
                # Check if progress changed
                if abs(current_progress - last_progress) > 0.001:
                    last_progress = current_progress
                    consecutive_no_change = 0
                else:
                    consecutive_no_change += 1
                
                # Send update
                data = job_status.model_dump_json()
                yield f"data: {data}\n\n"
                
                # Stop streaming if job is complete or failed
                if job_status.status in ("completed", "failed"):
                    yield "event: close\ndata: {}\n\n"
                    break
                
                # Stop if no progress for too long (job might be stuck)
                if consecutive_no_change > 60:  # 5 minutes at 5s intervals
                    yield "event: timeout\ndata: {}\n\n"
                    break
                
                # Wait before next update (5 second polling interval)
                await asyncio.sleep(5)
        finally:
            session.close()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
