"""Validate CSV headers and enforce field constraints."""

from __future__ import annotations

from typing import Any


class ValidationError(ValueError):
    """Custom exception for CSV validation errors."""

    pass


REQUIRED_HEADERS = ["sku", "name", "description"]


def validate_headers(headers: list[str] | None) -> None:
    """Ensure CSV contains the required columns before processing."""
    if not headers:
        raise ValidationError(
            "CSV requires a header row with sku,name,description columns"
        )
    normalized = [header.strip().lower() for header in headers]
    missing = [field for field in REQUIRED_HEADERS if field not in normalized]
    if missing:
        raise ValidationError(f"Missing required column(s): {', '.join(missing)}")


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Clean individual row (trim strings, enforce required fields)."""

    def _clean(key: str) -> str:
        value = row.get(key) or row.get(key.lower()) or row.get(key.upper())
        return value.strip() if isinstance(value, str) else ""

    sku = _clean("sku")
    name = _clean("name")
    description = _clean("description") or None

    if not sku:
        raise ValueError("Encountered a row with empty SKU; aborting import")
    if not name:
        raise ValueError(f"Row for SKU '{sku}' is missing a name")

    return {
        "sku": sku,
        "name": name,
        "description": description,
        "active": True,
    }
