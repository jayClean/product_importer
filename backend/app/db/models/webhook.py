"""SQLAlchemy model for webhook definitions."""
from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

from app.db.base import Base


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True)
    url = Column(Text, nullable=False)
    event = Column(String(64), nullable=False)
    enabled = Column(Boolean, default=True)
    secret = Column(String(255))
    last_test_status = Column(String(32))
    last_test_response_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
