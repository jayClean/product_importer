"""Business logic for chunked CSV ingestion."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterable

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.utils.csv_validator import ValidationError

logger = logging.getLogger(__name__)

from app.db.models.product import Product
from app.storage.s3_client import save_upload
from app.utils.csv_validator import normalize_row, validate_headers
from app.utils.memory_monitor import (
    check_memory_exceeded,
    check_memory_pressure,
    force_gc,
    log_memory_status,
)


async def stage_file(upload_file: UploadFile) -> Path:
    """Persist uploaded CSV to durable storage (S3/local) and return path."""
    try:
        await upload_file.seek(0)
        return save_upload(upload_file.file, upload_file.filename)
    except OSError as e:
        logger.error(f"OS error saving uploaded file: {e}", exc_info=True)
        raise ValueError(f"Failed to save file: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error saving uploaded file: {e}", exc_info=True)
        raise ValueError(f"Failed to save file: {str(e)}") from e


# Chunk size for CSV processing - adaptive based on memory pressure
# Base chunk size: 1000 rows for lower memory usage
# Reduced to 500 when memory pressure detected, 250 when high pressure
BASE_CHUNK_SIZE = 1000
REDUCED_CHUNK_SIZE = 500
MIN_CHUNK_SIZE = 250

def get_adaptive_chunk_size() -> int:
    """Get chunk size based on current memory pressure.
    
    Returns:
        Chunk size (number of rows) - smaller when memory pressure detected.
    """
    is_pressure, current, limit = check_memory_pressure()
    is_exceeded, _, _ = check_memory_exceeded()
    
    if is_exceeded:
        logger.warning("Memory limit exceeded, using minimum chunk size")
        return MIN_CHUNK_SIZE
    elif is_pressure:
        # Check how close we are to limit
        usage_ratio = current / limit if limit > 0 else 0
        if usage_ratio > 0.9:  # >90% of limit
            logger.warning("High memory pressure (>90%), using minimum chunk size")
            return MIN_CHUNK_SIZE
        else:
            logger.info("Memory pressure detected, using reduced chunk size")
            return REDUCED_CHUNK_SIZE
    else:
        return BASE_CHUNK_SIZE


def iter_csv_chunks(file_path: Path, chunk_size: int | None = None) -> Iterable[list[dict]]:
    """Yield parsed CSV rows (sku, name, description) in memory-safe batches.
    
    Processes rows in adaptive chunks based on memory pressure to optimize
    database writes and prevent OOM during large CSV imports.
    
    Args:
        file_path: Path to CSV file
        chunk_size: Optional fixed chunk size. If None, uses adaptive sizing.
    """
    try:
        # Use adaptive chunk size if not provided
        if chunk_size is None:
            chunk_size = get_adaptive_chunk_size()
            logger.info(f"Using adaptive chunk size: {chunk_size} rows")
        
        with file_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("CSV file appears to be empty or invalid")

            try:
                validate_headers(reader.fieldnames)
            except ValidationError as e:
                raise ValueError(f"Invalid CSV headers: {str(e)}") from e

            batch: list[dict] = []
            row_num = 1  # Start at 1 (header is row 0)
            chunks_yielded = 0
            
            for row in reader:
                row_num += 1
                
                # Check memory before processing each row (every 100 rows for performance)
                if row_num % 100 == 0:
                    is_exceeded, _, _ = check_memory_exceeded()
                    if is_exceeded:
                        logger.error("Memory limit exceeded during CSV processing, aborting")
                        raise MemoryError("Memory limit exceeded, cannot continue processing")
                    
                    # Adapt chunk size if memory pressure changes
                    adaptive_size = get_adaptive_chunk_size()
                    if adaptive_size < chunk_size:
                        chunk_size = adaptive_size
                        logger.info(f"Reduced chunk size to {chunk_size} due to memory pressure")
                
                try:
                    normalized = normalize_row(row)
                    batch.append(normalized)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error normalizing row {row_num}: {e}")
                    # Skip invalid rows but continue processing
                    continue

                if len(batch) >= chunk_size:
                    yield batch
                    chunks_yielded += 1
                    batch = []
                    
                    # Force garbage collection every 10 chunks to free memory
                    if chunks_yielded % 10 == 0:
                        force_gc()
                        log_memory_status(f"After {chunks_yielded} chunks")

            if batch:
                yield batch

    except FileNotFoundError:
        raise ValueError(f"CSV file not found: {file_path}")
    except PermissionError:
        raise ValueError(f"Permission denied reading file: {file_path}")
    except UnicodeDecodeError as e:
        raise ValueError(f"File encoding error: {str(e)}") from e
    except csv.Error as e:
        raise ValueError(f"CSV parsing error: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error reading CSV: {e}", exc_info=True)
        raise ValueError(f"Error reading CSV file: {str(e)}") from e


def count_rows(file_path: Path) -> int:
    """Return the total number of data rows in the CSV (excluding headers)."""
    try:
        with file_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("CSV file appears to be empty or invalid")

            try:
                validate_headers(reader.fieldnames)
            except ValidationError as e:
                raise ValueError(f"Invalid CSV headers: {str(e)}") from e

            return sum(1 for _ in reader)
    except FileNotFoundError:
        raise ValueError(f"CSV file not found: {file_path}")
    except PermissionError:
        raise ValueError(f"Permission denied reading file: {file_path}")
    except UnicodeDecodeError as e:
        raise ValueError(f"File encoding error: {str(e)}") from e
    except csv.Error as e:
        raise ValueError(f"CSV parsing error: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error counting CSV rows: {e}", exc_info=True)
        raise ValueError(f"Error reading CSV file: {str(e)}") from e


def upsert_products(rows: list[dict], db: Session) -> dict[str, int]:
    """Perform bulk upserts using SKU case-insensitive uniqueness."""
    if not rows:
        return {"inserted": 0, "updated": 0}

    try:
        # Normalize and deduplicate rows by SKU (case-insensitive)
        normalized_map: dict[str, dict] = {}
        for row in rows:
            if not row.get("sku"):
                logger.warning("Skipping row with missing SKU")
                continue
            sku_lower = row["sku"].lower().strip()
            if not sku_lower:
                logger.warning("Skipping row with empty SKU")
                continue
            normalized_map[sku_lower] = row

        if not normalized_map:
            return {"inserted": 0, "updated": 0}

        # Fetch existing products
        try:
            existing_products = (
                db.execute(
                    select(Product).where(
                        func.lower(Product.sku).in_(list(normalized_map.keys()))
                    )
                )
                .scalars()
                .all()
            )
        except SQLAlchemyError as e:
            logger.error(
                f"Database error fetching existing products: {e}", exc_info=True
            )
            raise

        # Update existing products
        updated = 0
        for product in existing_products:
            payload = normalized_map.pop(product.sku.lower(), None)
            if not payload:
                continue
            try:
                product.name = payload.get("name", "").strip()
                product.description = (
                    payload.get("description", "").strip()
                    if payload.get("description")
                    else None
                )
                product.active = payload.get("active", True)
                product.is_deleted = False  # Restore if was deleted
                updated += 1
            except Exception as e:
                logger.warning(f"Error updating product {product.id}: {e}")
                continue

        # Insert new products
        inserted = 0
        for payload in normalized_map.values():
            try:
                product = Product(
                    sku=payload.get("sku", "").strip(),
                    name=payload.get("name", "").strip(),
                    description=payload.get("description", "").strip()
                    if payload.get("description")
                    else None,
                    active=payload.get("active", True),
                    is_deleted=False,
                )
                db.add(product)
                inserted += 1
            except Exception as e:
                logger.warning(
                    f"Error creating product with SKU {payload.get('sku')}: {e}"
                )
                continue

        return {"inserted": inserted, "updated": updated}

    except SQLAlchemyError as e:
        logger.error(f"Database error in upsert_products: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upsert_products: {e}", exc_info=True)
        raise
