"""Engine and session factory configuration."""

from collections.abc import Generator
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Configure engine with connection pooling for long-running tasks
# pool_pre_ping: Test connections before using (handles stale connections)
# pool_recycle: Recycle connections after 30 minutes (prevents timeout)
# pool_size: Number of connections to maintain
# max_overflow: Additional connections beyond pool_size
engine = create_engine(
    settings.database_url,
    echo=False,
    future=True,
    poolclass=QueuePool,
    pool_pre_ping=True,  # Test connections before using
    pool_recycle=1800,  # Recycle connections after 30 minutes
    pool_size=5,  # Maintain 5 connections
    max_overflow=10,  # Allow up to 10 additional connections
    connect_args={
        "connect_timeout": 10,  # 10 second connection timeout
        "keepalives": 1,  # Send keepalive packets
        "keepalives_idle": 30,  # Start keepalives after 30 seconds idle
        "keepalives_interval": 10,  # Send keepalive every 10 seconds
        "keepalives_count": 5,  # Close connection after 5 failed keepalives
    },
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_fresh_session() -> Session:
    """Get a fresh database session, handling connection errors.

    This is useful for long-running tasks where connections might timeout.
    """
    try:
        return SessionLocal()
    except (OperationalError, DisconnectionError) as e:
        logger.warning(f"Connection error creating session: {e}, retrying...")
        # Force pool to reconnect
        engine.dispose()
        return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    """Yield a transactional session for request/worker lifecycles."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
