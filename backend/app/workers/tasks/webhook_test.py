"""Celery task for webhook test pings."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError

from app.db.models.webhook import Webhook
from app.db.session import SessionLocal
from app.services.webhook_dispatch import dispatch_event
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.workers.tasks.webhook_test")
def webhook_test_task(self, webhook_id: int):
    """Send synthetic payload to webhook and capture response metadata.

    Creates a test event payload and sends it to the webhook URL.
    Records the response status and timing in the webhook record.
    """
    session = SessionLocal()
    webhook: Webhook | None = None

    try:
        webhook = session.get(Webhook, webhook_id)
        if not webhook:
            logger.error(f"Webhook {webhook_id} not found")
            return

        if not webhook.enabled:
            logger.warning(f"Webhook {webhook_id} is disabled, skipping test")
            return

        # Create test payload based on event type
        test_payload = {
            "event": webhook.event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test": True,
            "data": {
                "message": "This is a test webhook payload",
                "webhook_id": webhook_id,
            },
        }

        # Dispatch webhook
        logger.info(f"Sending test payload to webhook {webhook_id}")
        result = dispatch_event(webhook, test_payload, db=session)

        if result["success"]:
            logger.info(
                f"Webhook {webhook_id} test succeeded: "
                f"status={result['status']}, time={result['response_time_ms']}ms"
            )
        else:
            logger.warning(
                f"Webhook {webhook_id} test failed: {result.get('error', 'Unknown error')}"
            )

    except SQLAlchemyError as e:
        if session:
            session.rollback()
        logger.error(
            f"Database error in webhook test task {webhook_id}: {e}", exc_info=True
        )
        raise
    except Exception as e:
        if session:
            session.rollback()
        logger.error(
            f"Unexpected error in webhook test task {webhook_id}: {e}",
            exc_info=True,
        )
        raise
    finally:
        if session:
            session.close()
