"""Alembic environment: runs migrations online against the settings URL or a supplied connection."""

from alembic import context
from sqlalchemy import Connection

from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.models import Base
from emi_copilot.repositories.database import create_database_engine


def _run_migrations_on_connection(connection: Connection) -> None:
    """Runs pending migrations on one connection inside a single transaction."""
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Migrates the connection a caller supplied, or else the database named in the settings."""
    supplied_connection = context.config.attributes.get("connection")
    if isinstance(supplied_connection, Connection):
        _run_migrations_on_connection(supplied_connection)
        return
    engine = create_database_engine(ApplicationSettings())
    try:
        with engine.connect() as connection:
            _run_migrations_on_connection(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline (--sql) migrations are not supported; run them against a database.")
run_migrations_online()
