"""Service for triggering webhooks on product events."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.webhook import Webhook
from app.services.webhook_dispatch import dispatch_event
from app.workers.tasks.webhook_dispatch_async import dispatch_webhook_async

logger = logging.getLogger(__name__)


def trigger_webhooks(
    event_type: str,
    payload: dict[str, Any],
    db: Session,
    async_dispatch: bool = True,
) -> None:
    """Trigger all enabled webhooks for a given event type.
    
    Args:
        event_type: Event type (e.g., "product.created", "product.updated")
        payload: Event payload to send
        db: Database session
        async_dispatch: If True, dispatch via Celery task (non-blocking)
                        If False, dispatch synchronously (blocking)
    """
    try:
        # Find all enabled webhooks for this event
        webhooks = db.query(Webhook).filter(
            Webhook.event == event_type,
            Webhook.enabled == True,
        ).all()
        
        if not webhooks:
            logger.debug(f"No enabled webhooks found for event {event_type}")
            return
        
        logger.info(f"Triggering {len(webhooks)} webhook(s) for event {event_type}")
        
        for webhook in webhooks:
            try:
                if async_dispatch:
                    # Dispatch asynchronously via Celery (non-blocking)
                    dispatch_webhook_async.delay(webhook.id, payload)
                    logger.debug(f"Enqueued async webhook {webhook.id} for event {event_type}")
                else:
                    # Dispatch synchronously (blocking, but immediate)
                    result = dispatch_event(webhook, payload, db)
                    if not result.get("success"):
                        logger.warning(
                            f"Webhook {webhook.id} delivery failed: {result.get('error')}"
                        )
            except Exception as e:
                logger.error(
                    f"Error triggering webhook {webhook.id} for event {event_type}: {e}",
                    exc_info=True,
                )
                # Continue with other webhooks even if one fails
                continue
                
    except Exception as e:
        logger.error(
            f"Unexpected error triggering webhooks for event {event_type}: {e}",
            exc_info=True,
        )
        # Don't raise - webhook failures shouldn't break the main operation


def build_product_payload(product: Any, event_type: str) -> dict[str, Any]:
    """Build webhook payload for product events.
    
    Args:
        product: Product model instance
        event_type: Event type (product.created, product.updated, product.deleted)
        
    Returns:
        Dictionary with event payload
    """
    return {
        "event": event_type,
        "timestamp": product.updated_at.isoformat() if product.updated_at else product.created_at.isoformat(),
        "data": {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "description": product.description,
            "active": product.active,
            "is_deleted": product.is_deleted,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None,
        },
    }


def build_import_payload(job_id: str, total_rows: int, processed_rows: int, inserted: int, updated: int) -> dict[str, Any]:
    """Build webhook payload for import completion events.
    
    Args:
        job_id: Import job ID
        total_rows: Total rows in CSV
        processed_rows: Rows processed
        inserted: Number of products inserted
        updated: Number of products updated
        
    Returns:
        Dictionary with event payload
    """
    return {
        "event": "import.completed",
        "timestamp": None,  # Will be set by caller
        "data": {
            "job_id": job_id,
            "total_rows": total_rows,
            "processed_rows": processed_rows,
            "inserted": inserted,
            "updated": updated,
            "status": "completed",
        },
    }

