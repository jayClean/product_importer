"""Abstraction over object storage for uploads (local fs implementation)."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings

settings = get_settings()
# Config validator should have resolved this to absolute path, but ensure it's absolute
UPLOADS_DIR = Path(settings.uploads_dir).resolve()
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def save_upload(file_obj: BinaryIO, original_name: str | None = None) -> Path:
    """Persist uploaded CSV to local disk and return the absolute path."""
    suffix = Path(original_name or "upload.csv").suffix or ".csv"
    target_name = f"{uuid.uuid4()}{suffix}"
    target_path = (UPLOADS_DIR / target_name).resolve()
    file_obj.seek(0)
    with target_path.open("wb") as destination:
        shutil.copyfileobj(file_obj, destination)
    return target_path


def delete_upload(uri: str | Path) -> None:
    """Cleanup staged files when imports finish."""
    path = Path(uri)
    # Resolve to absolute path to ensure we're deleting the right file
    if not path.is_absolute():
        path = path.resolve()
    try:
        path.unlink(missing_ok=True)
    except OSError:
        # Intentionally swallow deletion errors; retention job can retry.
        pass
