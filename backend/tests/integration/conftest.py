"""Integration fixtures: the Compose PostgreSQL test database, migrated once, isolated per test.

Each test runs inside one outer transaction that is rolled back at the end. Sessions join it
through savepoints, so a unit of work's commit is real to the code under test but never
outlives the test. Nothing is ever deleted, which also suits the append-only audit_event trigger.
"""

from collections.abc import Iterator

import pytest
from alembic import command
from pydantic import SecretStr
from sqlalchemy import Connection, Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.repositories.database import create_database_engine
from tests.fixed_clock import FixedClock
from tests.integration.migration_runner import build_alembic_config
from tests.payment_builders import CREATED_AT

# ADR 0007: integration tests use this separate database, never the development one.
TEST_DATABASE_NAME = "emi_copilot_test"


@pytest.fixture(scope="session")
def test_database_engine() -> Iterator[Engine]:
    """Connects to the test database (same server and user as the settings) and migrates it."""
    configured_database_url = make_url(ApplicationSettings().database_url.get_secret_value())
    test_database_url = configured_database_url.set(database=TEST_DATABASE_NAME)
    engine = create_database_engine(
        ApplicationSettings(
            database_url=SecretStr(test_database_url.render_as_string(hide_password=False))
        )
    )
    with engine.begin() as connection:
        command.upgrade(build_alembic_config(connection), "head")
    yield engine
    engine.dispose()


@pytest.fixture
def database_connection(test_database_engine: Engine) -> Iterator[Connection]:
    """Opens a connection whose outer transaction is rolled back after the test."""
    with test_database_engine.connect() as connection:
        outer_transaction = connection.begin()
        yield connection
        outer_transaction.rollback()


@pytest.fixture
def session_factory(database_connection: Connection) -> sessionmaker[Session]:
    """Builds sessions that commit to savepoints inside the test's outer transaction."""
    return sessionmaker(
        bind=database_connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )


@pytest.fixture
def fixed_clock() -> FixedClock:
    """Gives repositories a clock that only moves when the test moves it."""
    return FixedClock(CREATED_AT)
