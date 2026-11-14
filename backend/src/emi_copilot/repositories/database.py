"""Builds the SQLAlchemy engine and session factory from the application settings."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.config.settings import ApplicationSettings


def create_database_engine(settings: ApplicationSettings) -> Engine:
    """Creates a pooled engine for the configured database; stale pooled connections are renewed."""
    return create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Creates the session factory a unit of work opens; loaded rows stay readable after commit."""
    return sessionmaker(bind=engine, expire_on_commit=False)
