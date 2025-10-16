from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy import create_engine
from alembic import context

# Ensure project src is importable when running `alembic` from container root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import settings and models to expose metadata
from src.core.config import get_settings
from src.models import Base  # noqa: F401

# Alembic Config object, provides access to values within alembic.ini
config = context.config

# Setup Python logging via config file if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata

# Use DATABASE_URL from env/pydantic settings
settings = get_settings()
db_url = settings.DATABASE_URL

# Configure sqlalchemy.url programmatically to override alembic.ini placeholder
config.set_main_option("sqlalchemy.url", db_url)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    This creates an Engine and associates a connection with the context.
    """
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
