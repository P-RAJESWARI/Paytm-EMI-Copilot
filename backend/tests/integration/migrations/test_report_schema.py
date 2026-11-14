"""Integration tests for migration 0005: weekly_message and the funnel stage index."""

from collections.abc import Iterator
from datetime import date

import pytest
from alembic import command
from sqlalchemy import Connection, Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from tests.integration.migration_runner import build_alembic_config

pytestmark = pytest.mark.integration

SCRATCH_SCHEMA = "report_migration_scratch"
INSERT_WEEKLY_MESSAGE = text(
    "INSERT INTO weekly_message VALUES (:id, :merchant_id, :period_start_date, now(), now(), now())"
)
INSERT_MERCHANT = text(
    "INSERT INTO merchant VALUES ('01JCMERCHANT00000000000001', 'SHOP-0001', 'Shop',"
    " 'Counter tablet 1', :pin_hash, :pin_salt, 0, NULL, now(), now())"
)


@pytest.fixture
def scratch_schema_connection(test_database_engine: Engine) -> Iterator[Connection]:
    """Gives a connection whose only schema is an empty scratch one, discarded by rollback."""
    with test_database_engine.connect() as connection:
        outer_transaction = connection.begin()
        connection.execute(text(f"CREATE SCHEMA {SCRATCH_SCHEMA}"))
        connection.execute(text(f"SET LOCAL search_path TO {SCRATCH_SCHEMA}"))
        yield connection
        outer_transaction.rollback()


def test_migration_0005_creates_and_removes_weekly_message_and_the_stage_index(
    scratch_schema_connection: Connection,
) -> None:
    """0005 adds the table and index; going back to 0004 removes both."""
    alembic_config = build_alembic_config(scratch_schema_connection)
    command.upgrade(alembic_config, "0005")
    database_inspector = inspect(scratch_schema_connection)
    assert "weekly_message" in database_inspector.get_table_names(schema=SCRATCH_SCHEMA)
    funnel_index_names = {
        index["name"]
        for index in database_inspector.get_indexes("funnel_event", schema=SCRATCH_SCHEMA)
    }
    assert "ix_funnel_event_merchant_id_stage_occurred_at" in funnel_index_names
    command.downgrade(alembic_config, "0004")
    database_inspector = inspect(scratch_schema_connection)
    assert "weekly_message" not in database_inspector.get_table_names(schema=SCRATCH_SCHEMA)
    assert "ix_funnel_event_merchant_id_stage_occurred_at" not in {
        index["name"]
        for index in database_inspector.get_indexes("funnel_event", schema=SCRATCH_SCHEMA)
    }


def test_weekly_message_is_unique_per_shop_and_week_and_keyed_by_a_monday(
    database_connection: Connection,
) -> None:
    """The unique key leads with merchant_id (its index); a Tuesday week start is refused."""
    database_inspector = inspect(database_connection)
    (unique_constraint,) = database_inspector.get_unique_constraints("weekly_message")
    assert unique_constraint["column_names"] == ["merchant_id", "period_start_date"]
    columns = {column["name"] for column in database_inspector.get_columns("weekly_message")}
    assert columns == {
        "id",
        "merchant_id",
        "period_start_date",
        "sent_at",
        "created_at",
        "updated_at",
    }
    database_connection.execute(INSERT_MERCHANT, {"pin_hash": "c" * 64, "pin_salt": "d" * 32})
    savepoint = database_connection.begin_nested()
    with pytest.raises(IntegrityError, match="period_start_date_is_monday"):
        database_connection.execute(
            INSERT_WEEKLY_MESSAGE,
            {
                "id": "01JCWEEKLYMESSAGE000000001",
                "merchant_id": "01JCMERCHANT00000000000001",
                "period_start_date": date(2026, 11, 10),
            },
        )
    savepoint.rollback()
