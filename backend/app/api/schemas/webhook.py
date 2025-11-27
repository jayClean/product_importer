"""Webhook configuration schemas."""

from datetime import datetime

from pydantic import BaseModel, AnyHttpUrl, Field, field_serializer


class WebhookBase(BaseModel):
    url: AnyHttpUrl
    event: str = Field(..., description="Event type to subscribe to")
    enabled: bool = True


class WebhookCreate(WebhookBase):
    secret: str | None = Field(None, description="Optional signing secret")


class WebhookUpdate(BaseModel):
    url: AnyHttpUrl | None = None
    event: str | None = None
    enabled: bool | None = None
    secret: str | None = None


class WebhookRead(WebhookBase):
    id: int
    secret: str | None = None
    last_test_status: str | None = None
    last_test_response_ms: int | None = None
    created_at: datetime | None = None

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str | None:
        """Convert datetime to ISO format string."""
        if value is None:
            return None
        return value.isoformat()

    model_config = {"from_attributes": True}
