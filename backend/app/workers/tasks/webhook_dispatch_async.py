"""Celery task for asynchronous webhook dispatch."""

from __future__ import annotations

import logging
from typing import Any

from app.db.models.webhook import Webhook
from app.db.session import get_fresh_session
from app.services.webhook_dispatch import dispatch_event
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.workers.tasks.webhook_dispatch_async")
def dispatch_webhook_async(self, webhook_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Dispatch webhook asynchronously via Celery.
    
    This allows webhook delivery to be non-blocking for the main application flow.
    
    Args:
        webhook_id: Webhook ID to dispatch
        payload: Event payload to send
        
    Returns:
        Dispatch result dictionary
    """
    session = get_fresh_session()
    try:
        webhook = session.get(Webhook, webhook_id)
        if not webhook:
            logger.error(f"Webhook {webhook_id} not found")
            return {"success": False, "error": "Webhook not found"}
        
        if not webhook.enabled:
            logger.warning(f"Webhook {webhook_id} is disabled, skipping dispatch")
            return {"success": False, "error": "Webhook is disabled"}
        
        # Dispatch the webhook
        result = dispatch_event(webhook, payload, session)
        
        logger.info(
            f"Async webhook {webhook_id} dispatched: "
            f"success={result.get('success')}, status={result.get('status')}"
        )
        
        return result
        
    except Exception as e:
        logger.error(
            f"Error dispatching async webhook {webhook_id}: {e}",
            exc_info=True,
        )
        return {"success": False, "error": str(e)}
    finally:
        session.close()

