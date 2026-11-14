"""Tests for the engine and session factory built from settings (no database connection made)."""

from pydantic import SecretStr

from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.repositories.database import create_database_engine, create_session_factory

SAMPLE_DATABASE_URL = "postgresql+psycopg://sample_user@db.invalid:5432/sample"


def test_create_database_engine_uses_the_configured_url() -> None:
    """The engine targets exactly the database named in the settings."""
    engine = create_database_engine(
        ApplicationSettings(database_url=SecretStr(SAMPLE_DATABASE_URL))
    )
    assert engine.url.render_as_string(hide_password=False) == SAMPLE_DATABASE_URL
    engine.dispose()


def test_create_session_factory_binds_engine_and_keeps_objects_loaded_after_commit() -> None:
    """Sessions use the given engine and do not expire loaded rows on commit."""
    engine = create_database_engine(
        ApplicationSettings(database_url=SecretStr(SAMPLE_DATABASE_URL))
    )
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        assert session.get_bind() is engine
    assert session_factory.kw["expire_on_commit"] is False
    engine.dispose()
