"""Deliver webhook payloads and record responses."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models.webhook import Webhook

logger = logging.getLogger(__name__)
TIMEOUT_SECONDS = 10


def _sign_payload(payload: dict, secret: str) -> str:
    """Generate HMAC signature for webhook payload."""
    payload_str = json.dumps(payload, sort_keys=True)
    signature = hmac.new(
        secret.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def dispatch_event(
    webhook: Webhook,
    payload: dict[str, Any],
    db: Session | None = None,
) -> dict[str, Any]:
    """Send HTTP request to webhook URL and return status metrics.

    Args:
        webhook: Webhook configuration
        payload: Event payload to send
        db: Optional database session for recording results

    Returns:
        Dictionary with:
            - status: HTTP status code or error string
            - response_time_ms: Response time in milliseconds
            - success: Boolean indicating if delivery succeeded
            - error: Error message if failed
    """
    start_time = time.time()
    result: dict[str, Any] = {
        "status": None,
        "response_time_ms": None,
        "success": False,
        "error": None,
    }

    try:
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Acme-Product-Importer/1.0",
        }

        # Add signature if secret is configured
        if webhook.secret:
            signature = _sign_payload(payload, webhook.secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        # Prepare request body
        request_body = json.dumps(payload)

        # Send HTTP request
        with httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = client.post(
                webhook.url,
                content=request_body,
                headers=headers,
            )

            elapsed_ms = int((time.time() - start_time) * 1000)
            result["response_time_ms"] = elapsed_ms
            result["status"] = response.status_code
            result["success"] = 200 <= response.status_code < 300

            if not result["success"]:
                result["error"] = f"HTTP {response.status_code}: {response.text[:200]}"

            logger.info(
                f"Webhook {webhook.id} delivered: status={result['status']}, "
                f"time={elapsed_ms}ms"
            )

    except httpx.TimeoutException as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["response_time_ms"] = elapsed_ms
        result["status"] = "timeout"
        result["error"] = f"Request timeout after {TIMEOUT_SECONDS}s"
        logger.warning(f"Webhook {webhook.id} timeout: {e}")

    except httpx.RequestError as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["response_time_ms"] = elapsed_ms
        result["status"] = "error"
        result["error"] = f"Request failed: {str(e)}"
        logger.error(f"Webhook {webhook.id} request error: {e}", exc_info=True)

    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        result["response_time_ms"] = elapsed_ms
        result["status"] = "error"
        result["error"] = f"Unexpected error: {str(e)}"
        logger.error(f"Webhook {webhook.id} unexpected error: {e}", exc_info=True)

    # Record results in database if session provided
    if db:
        try:
            record_delivery(webhook, result, db)
        except Exception as e:
            logger.error(
                f"Failed to record webhook delivery for {webhook.id}: {e}",
                exc_info=True,
            )

    return result


def record_delivery(
    webhook: Webhook,
    result: dict[str, Any],
    db: Session,
) -> None:
    """Store response info for UI visibility and retries.

    Updates the webhook's last_test_status and last_test_response_ms fields.
    """
    try:
        status_str = str(result.get("status", "unknown"))
        if len(status_str) > 32:
            status_str = status_str[:32]

        webhook.last_test_status = status_str
        webhook.last_test_response_ms = result.get("response_time_ms")

        db.commit()
        logger.debug(f"Recorded delivery result for webhook {webhook.id}")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Database error recording webhook delivery {webhook.id}: {e}",
            exc_info=True,
        )
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error recording webhook delivery {webhook.id}: {e}",
            exc_info=True,
        )
        raise
