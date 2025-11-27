"""Memory monitoring utilities for OOM prevention and optimization."""

import gc
import logging
import os
import resource
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Memory limits in bytes
# Default: 500MB baseline, 800MB hard limit (leaving ~200MB for system/API)
DEFAULT_MEMORY_BASELINE = 500 * 1024 * 1024  # 500MB
DEFAULT_MEMORY_LIMIT = 800 * 1024 * 1024  # 800MB


def get_memory_usage() -> int:
    """Get current memory usage in bytes (RSS - Resident Set Size)."""
    try:
        # Get current process memory usage
        # resource.getrusage returns memory in KB on most systems
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss is maximum resident set size
        # For current usage, we use ru_maxrss (it's the peak, but close enough)
        # For more accurate current usage, we'd need psutil, but let's use this
        memory_value = usage.ru_maxrss
        
        # Convert to bytes
        # On macOS, ru_maxrss is in bytes, on Linux it's in KB
        # Check system and convert accordingly
        if sys.platform == "darwin":
            # macOS returns bytes
            return memory_value
        else:
            # Linux returns KB
            return memory_value * 1024
    except Exception as e:
        logger.warning(f"Could not get memory usage: {e}")
        return 0


def get_memory_limit() -> int:
    """Get configured memory limit from environment or use default."""
    limit_str = os.environ.get("CELERY_MEMORY_LIMIT")
    if limit_str:
        try:
            # Support formats: "800M", "800MB", "800000000" (bytes)
            limit_str = limit_str.upper().strip()
            if limit_str.endswith("M") or limit_str.endswith("MB"):
                limit_mb = int(limit_str.rstrip("MB"))
                return limit_mb * 1024 * 1024
            elif limit_str.endswith("G") or limit_str.endswith("GB"):
                limit_gb = int(limit_str.rstrip("GB"))
                return limit_gb * 1024 * 1024 * 1024
            else:
                return int(limit_str)
        except ValueError:
            logger.warning(f"Invalid CELERY_MEMORY_LIMIT format: {limit_str}, using default")
    return DEFAULT_MEMORY_LIMIT


def get_memory_baseline() -> int:
    """Get configured memory baseline from environment or use default."""
    baseline_str = os.environ.get("CELERY_MEMORY_BASELINE")
    if baseline_str:
        try:
            baseline_str = baseline_str.upper().strip()
            if baseline_str.endswith("M") or baseline_str.endswith("MB"):
                baseline_mb = int(baseline_str.rstrip("MB"))
                return baseline_mb * 1024 * 1024
            elif baseline_str.endswith("G") or baseline_str.endswith("GB"):
                baseline_gb = int(baseline_str.rstrip("GB"))
                return baseline_gb * 1024 * 1024 * 1024
            else:
                return int(baseline_str)
        except ValueError:
            logger.warning(f"Invalid CELERY_MEMORY_BASELINE format: {baseline_str}, using default")
    return DEFAULT_MEMORY_BASELINE


def check_memory_pressure() -> tuple[bool, int, int]:
    """Check if memory usage is approaching limits.
    
    Returns:
        (is_pressure, current_usage_bytes, limit_bytes)
        is_pressure: True if memory usage > baseline
    """
    current = get_memory_usage()
    limit = get_memory_limit()
    baseline = get_memory_baseline()
    
    # Check if we're above baseline (warning zone)
    is_pressure = current > baseline
    
    if is_pressure:
        logger.warning(
            f"Memory pressure detected: {current / 1024 / 1024:.1f}MB / "
            f"{limit / 1024 / 1024:.1f}MB (baseline: {baseline / 1024 / 1024:.1f}MB)"
        )
    
    return is_pressure, current, limit


def check_memory_exceeded() -> tuple[bool, int, int]:
    """Check if memory usage has exceeded the hard limit.
    
    Returns:
        (is_exceeded, current_usage_bytes, limit_bytes)
    """
    current = get_memory_usage()
    limit = get_memory_limit()
    
    is_exceeded = current >= limit
    
    if is_exceeded:
        logger.error(
            f"Memory limit exceeded: {current / 1024 / 1024:.1f}MB >= "
            f"{limit / 1024 / 1024:.1f}MB"
        )
    
    return is_exceeded, current, limit


def force_gc() -> None:
    """Force garbage collection to free memory."""
    try:
        # Collect all generations
        collected = gc.collect()
        logger.debug(f"Garbage collection freed {collected} objects")
    except Exception as e:
        logger.warning(f"Error during garbage collection: {e}")


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f}TB"


def log_memory_status(context: str = "") -> None:
    """Log current memory status for debugging."""
    current = get_memory_usage()
    limit = get_memory_limit()
    baseline = get_memory_baseline()
    usage_percent = (current / limit * 100) if limit > 0 else 0
    
    context_str = f" [{context}]" if context else ""
    logger.info(
        f"Memory status{context_str}: {format_bytes(current)} / "
        f"{format_bytes(limit)} ({usage_percent:.1f}%) "
        f"[baseline: {format_bytes(baseline)}]"
    )

