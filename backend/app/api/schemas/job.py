"""Async job status payloads."""

from datetime import datetime
from pydantic import BaseModel, Field


class JobStatus(BaseModel):
    id: str
    type: str = Field(..., description="e.g., import_products, webhook_test")
    status: str = Field(..., description="pending|running|failed|completed")
    progress: float | None = Field(None, description="0-1 range for UI progress bars")
    message: str | None = None
    total_rows: int | None = None
    processed_rows: int | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    meta: dict | None = None
