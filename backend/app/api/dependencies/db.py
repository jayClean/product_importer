"""Database session dependency."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import get_db


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a managed SQLAlchemy session."""
    yield from get_db()
