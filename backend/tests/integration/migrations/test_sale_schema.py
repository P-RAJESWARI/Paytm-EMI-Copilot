"""Integration tests for migration 0004: sale, funnel_event, the sale link and audit types."""

from collections.abc import Iterator

import pytest
from alembic import command
from sqlalchemy import Connection, Engine, inspect, text

from tests.integration.migration_runner import build_alembic_config

pytestmark = pytest.mark.integration

SCRATCH_SCHEMA = "sale_migration_scratch"
SALE_TABLES = {"sale", "funnel_event"}
INSERT_SALE_AUDIT_ROW = (
    "INSERT INTO audit_event VALUES ('01JCAUDITSCRATCH0000000001', 'SALE_STARTED', 'sale',"
    " '01JCSALE000000000000000001', NULL, now(), '{}'::jsonb, now())"
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


def _table_names(connection: Connection) -> set[str]:
    """Lists the tables currently in the scratch schema."""
    return set(inspect(connection).get_table_names(schema=SCRATCH_SCHEMA))


def _payment_attempt_column_names(connection: Connection) -> set[str]:
    """Lists the payment_attempt columns currently in the scratch schema."""
    return {
        column["name"]
        for column in inspect(connection).get_columns("payment_attempt", schema=SCRATCH_SCHEMA)
    }


def test_migration_0004_creates_and_removes_sale_tables_and_the_attempt_link(
    scratch_schema_connection: Connection,
) -> None:
    """0004 adds sale, funnel_event and payment_attempt.sale_id; going back to 0003 drops them."""
    alembic_config = build_alembic_config(scratch_schema_connection)
    command.upgrade(alembic_config, "0003")
    assert not SALE_TABLES & _table_names(scratch_schema_connection)
    command.upgrade(alembic_config, "0004")
    assert _table_names(scratch_schema_connection) >= SALE_TABLES
    assert "sale_id" in _payment_attempt_column_names(scratch_schema_connection)
    command.downgrade(alembic_config, "0003")
    assert not SALE_TABLES & _table_names(scratch_schema_connection)
    assert "sale_id" not in _payment_attempt_column_names(scratch_schema_connection)


def test_migration_0004_downgrade_keeps_sale_audit_rows_it_cannot_delete(
    scratch_schema_connection: Connection,
) -> None:
    """audit_event is append-only, so the restored type check is NOT VALID and the row survives."""
    alembic_config = build_alembic_config(scratch_schema_connection)
    command.upgrade(alembic_config, "0004")
    scratch_schema_connection.execute(text(INSERT_SALE_AUDIT_ROW))
    command.downgrade(alembic_config, "0003")
    remaining_rows = scratch_schema_connection.execute(
        text("SELECT count(*) FROM audit_event WHERE event_type = 'SALE_STARTED'")
    ).scalar_one()
    assert remaining_rows == 1
    command.upgrade(alembic_config, "head")


@pytest.mark.parametrize(
    ("table_name", "foreign_key_column"),
    [
        ("sale", "merchant_id"),
        ("sale", "product_id"),
        ("funnel_event", "sale_id"),
        ("funnel_event", "merchant_id"),
        ("payment_attempt", "sale_id"),
    ],
)
def test_every_new_foreign_key_leads_an_index(
    database_connection: Connection, table_name: str, foreign_key_column: str
) -> None:
    """backend.md section 8: each foreign key is the first column of an index or unique key."""
    database_inspector = inspect(database_connection)
    leading_columns = {
        index["column_names"][0] for index in database_inspector.get_indexes(table_name)
    } | {
        constraint["column_names"][0]
        for constraint in database_inspector.get_unique_constraints(table_name)
    }
    assert foreign_key_column in leading_columns


def test_sale_has_the_counter_and_report_indexes(database_connection: Connection) -> None:
    """(merchant, status) and (merchant, started_at) serve the counter list and the reports."""
    indexes = {
        index["name"]: (index["column_names"], index["unique"])
        for index in inspect(database_connection).get_indexes("sale")
        if "duplicates_constraint" not in index
    }
    assert indexes == {
        "ix_sale_product_id": (["product_id"], False),
        "ix_sale_merchant_id_status": (["merchant_id", "status"], False),
        "ix_sale_merchant_id_started_at": (["merchant_id", "started_at"], False),
        "uq_sale_merchant_id_session_code_open": (["merchant_id", "session_code"], True),
    }


def test_open_session_code_index_covers_only_open_statuses(
    database_connection: Connection,
) -> None:
    """Paid and expired sales free their code; the predicate names the three open statuses."""
    index_definition = database_connection.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = :name"),
        {"name": "uq_sale_merchant_id_session_code_open"},
    ).scalar_one()
    for open_status in ("CHOOSING", "PAYMENT_NOT_COMPLETED", "READY_TO_PAY"):
        assert open_status in index_definition
    assert "'PAID'" not in index_definition
    assert "EXPIRED" not in index_definition


def test_sale_tables_hold_money_as_bigint_paise_and_funnel_has_no_updated_at(
    database_connection: Connection,
) -> None:
    """Money is BIGINT paise; funnel_event is append-only; sale carries the usual timestamps."""
    database_inspector = inspect(database_connection)
    sale_columns = {column["name"]: column for column in database_inspector.get_columns("sale")}
    funnel_columns = {
        column["name"]: column for column in database_inspector.get_columns("funnel_event")
    }
    assert str(sale_columns["price_in_paise"]["type"]) == "BIGINT"
    assert str(funnel_columns["monthly_budget_in_paise"]["type"]) == "BIGINT"
    assert {"id", "created_at", "updated_at"} <= set(sale_columns)
    assert "updated_at" not in funnel_columns
    assert "qr_token" not in sale_columns
    assert "qr_token_nonce_hash" in sale_columns


def test_audit_event_accepts_the_sale_event_types(database_connection: Connection) -> None:
    """The type check now lists the three sale audit types beside the Layer 1 ones."""
    check_definition = database_connection.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
            " WHERE conname = 'ck_audit_event_event_type_known'"
        )
    ).scalar_one()
    for event_type in ("SALE_STARTED", "SALE_STATUS_CHANGED", "SALE_PAYMENT_OUTCOME_IGNORED"):
        assert event_type in check_definition
    assert "OFFER_QUOTE_MISMATCH" in check_definition
