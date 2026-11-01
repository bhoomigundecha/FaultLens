"""
Alembic migration environment — FaultLens Backend

Uses the synchronous DATABASE_URL_SYNC for Alembic (asyncpg is not
compatible with Alembic's synchronous migration runner).

Automatically picks up DATABASE_URL_SYNC from the .env file via
app.core.config so there is a single source of truth.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Make the `app` package importable from the backend root ──────────────────
# Alembic runs from the backend/ directory, so backend/ must be on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings
from app.db.session import Base  # noqa: F401 — ensures Base.metadata is available
import app.models  # noqa: F401 — registers all ORM tables in Base.metadata

# ── Alembic config object ─────────────────────────────────────────────────────
config = context.config

# Configure Python logging from alembic.ini (but don't override our app logger)
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# ── SQLAlchemy metadata ───────────────────────────────────────────────────────
# Point at Base.metadata so alembic autogenerate can detect model changes.
# As we add ORM models in later phases, they must be imported here (or via
# app.models.__init__) so their tables are registered in Base.metadata.
target_metadata = Base.metadata


def get_url() -> str:
    """Return the synchronous DB URL for Alembic migrations."""
    settings = get_settings()
    url = settings.database_url_sync or settings.database_url

    # Strip asyncpg driver if someone accidentally set the async URL
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgresql+aiosqlite://", "sqlite:///")

    if not url:
        raise RuntimeError(
            "DATABASE_URL_SYNC (or DATABASE_URL) must be set to run migrations."
        )
    return url


def run_migrations_offline() -> None:
    """
    Offline mode: generate SQL script without a live DB connection.
    Useful for review / CI diff checks.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Online mode: connect to the live database and apply migrations.
    Uses NullPool because Alembic creates its own short-lived connection.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,          # detect column type changes
            compare_server_default=True, # detect default value changes
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
