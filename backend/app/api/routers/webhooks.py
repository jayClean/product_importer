"""Webhook configuration endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies.db import get_session
from app.api.schemas.webhook import WebhookCreate, WebhookRead, WebhookUpdate
from app.db.models.webhook import Webhook
from app.services.webhook_dispatch import dispatch_event
from app.workers.tasks.webhook_test import webhook_test_task

logger = logging.getLogger(__name__)
router = APIRouter()

# Valid event types
VALID_EVENTS = [
    "product.created",
    "product.updated",
    "product.deleted",
    "import.completed",
]


@router.get(
    "/",
    summary="List registered webhooks",
    response_model=list[WebhookRead],
)
async def list_webhooks(
    db: Session = Depends(get_session),
) -> list[WebhookRead]:
    """Return webhook definitions with status info for the management UI."""
    try:
        webhooks = db.query(Webhook).order_by(Webhook.created_at.desc()).all()
        return [WebhookRead.model_validate(w) for w in webhooks]
    except SQLAlchemyError as e:
        logger.error(f"Database error while listing webhooks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve webhooks",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error while listing webhooks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.post(
    "/",
    summary="Create a webhook",
    status_code=status.HTTP_201_CREATED,
    response_model=WebhookRead,
)
async def create_webhook(
    payload: WebhookCreate,
    db: Session = Depends(get_session),
) -> WebhookRead:
    """Add a webhook URL/event mapping from UI forms.

    Validates event type and URL format. The webhook is enabled by default.
    """
    try:
        # Validate event type
        if payload.event not in VALID_EVENTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type. Must be one of: {', '.join(VALID_EVENTS)}",
            )

        # Validate URL is reachable (basic check)
        url_str = str(payload.url)
        if not url_str.startswith(("http://", "https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL must start with http:// or https://",
            )

        # Create webhook
        webhook = Webhook(
            url=url_str,
            event=payload.event,
            enabled=payload.enabled,
            secret=payload.secret,
        )
        db.add(webhook)
        db.commit()
        db.refresh(webhook)

        logger.info(f"Created webhook {webhook.id} for event {payload.event}")
        return WebhookRead.model_validate(webhook)

    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create webhook. Check for duplicate entries.",
        ) from e
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error creating webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create webhook",
        ) from e
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.put(
    "/{webhook_id}",
    summary="Update webhook",
    response_model=WebhookRead,
)
async def update_webhook(
    webhook_id: int,
    payload: WebhookUpdate,
    db: Session = Depends(get_session),
) -> WebhookRead:
    """Persist edits to URL, events, or enablement toggles.

    Only provided fields are updated (partial update).
    """
    try:
        webhook = db.get(Webhook, webhook_id)
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        # Validate event type if provided
        if payload.event is not None and payload.event not in VALID_EVENTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid event type. Must be one of: {', '.join(VALID_EVENTS)}",
            )

        # Validate URL if provided
        if payload.url is not None:
            url_str = str(payload.url)
            if not url_str.startswith(("http://", "https://")):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="URL must start with http:// or https://",
                )
            webhook.url = url_str

        # Apply updates
        if payload.event is not None:
            webhook.event = payload.event
        if payload.enabled is not None:
            webhook.enabled = payload.enabled
        if payload.secret is not None:
            webhook.secret = payload.secret

        db.commit()
        db.refresh(webhook)

        logger.info(f"Updated webhook {webhook_id}")
        return WebhookRead.model_validate(webhook)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Database error updating webhook {webhook_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update webhook",
        ) from e
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error updating webhook {webhook_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.delete(
    "/{webhook_id}",
    summary="Delete webhook",
)
async def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_session),
) -> Response:
    """Remove webhook definitions after confirmation."""
    try:
        webhook = db.get(Webhook, webhook_id)
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        db.delete(webhook)
        db.commit()

        logger.info(f"Deleted webhook {webhook_id}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Database error deleting webhook {webhook_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete webhook",
        ) from e
    except Exception as e:
        db.rollback()
        logger.error(
            f"Unexpected error deleting webhook {webhook_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e


@router.post(
    "/{webhook_id}/test",
    summary="Trigger webhook test delivery",
    status_code=status.HTTP_202_ACCEPTED,
)
async def test_webhook(
    webhook_id: int,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    """Fire async delivery job to capture response code/time metrics.

    Returns immediately with task ID. The webhook will receive a test payload
    and the response will be recorded in the webhook's last_test_status and
    last_test_response_ms fields.
    """
    try:
        webhook = db.get(Webhook, webhook_id)
        if not webhook:
            raise HTTPException(status_code=404, detail="Webhook not found")

        if not webhook.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot test disabled webhook",
            )

        # Enqueue async test task
        task = webhook_test_task.delay(webhook_id)

        logger.info(f"Enqueued test task for webhook {webhook_id}, task_id={task.id}")
        return {
            "message": "Webhook test enqueued",
            "task_id": task.id,
            "webhook_id": webhook_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enqueueing webhook test {webhook_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue webhook test",
        ) from e
