from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.core.config import get_settings
from src.models import Base  # Ensure models are imported so metadata is populated

_settings = get_settings()

# Create SQLAlchemy engine and session factory
engine = create_engine(_settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)

# Expose Base for Alembic and metadata access
# PUBLIC_INTERFACE
def get_base() -> Base.__class__:
    """Return SQLAlchemy Declarative Base for migrations and metadata operations."""
    return Base


# PUBLIC_INTERFACE
@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
