"""Integration tests for the migrations: reversibility, constraints, indexes and no drift."""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, Engine, inspect, text

from emi_copilot.models import Base
from tests.integration.migration_runner import build_alembic_config

pytestmark = pytest.mark.integration

SCRATCH_SCHEMA = "migration_round_trip_scratch"
APPLICATION_TABLES = {"payment_attempt", "audit_event", "merchant", "device_pairing", "product"}
MERCHANT_TABLES = ("merchant", "device_pairing", "product")
CARD_FIELD_WORDS = ("card", "cvv", "expiry", "bin")


@pytest.fixture
def scratch_schema_connection(test_database_engine: Engine) -> Iterator[Connection]:
    """Gives a connection whose only schema is an empty scratch one, discarded by rollback."""
    with test_database_engine.connect() as connection:
        outer_transaction = connection.begin()
        connection.execute(text(f"CREATE SCHEMA {SCRATCH_SCHEMA}"))
        connection.execute(text(f"SET LOCAL search_path TO {SCRATCH_SCHEMA}"))
        yield connection
        outer_transaction.rollback()


def _scratch_table_names(connection: Connection) -> set[str]:
    """Lists the tables currently in the scratch schema."""
    return set(inspect(connection).get_table_names(schema=SCRATCH_SCHEMA))


def _scratch_guard_function_count(connection: Connection) -> int:
    """Counts the audit guard functions currently in the scratch schema."""
    return int(
        connection.execute(
            text(
                "SELECT count(*) FROM pg_proc JOIN pg_namespace ON pg_namespace.oid = pronamespace"
                " WHERE nspname = :schema AND proname = 'reject_audit_event_modification'"
            ),
            {"schema": SCRATCH_SCHEMA},
        ).scalar_one()
    )


def test_migration_upgrade_downgrade_upgrade_round_trip(
    scratch_schema_connection: Connection,
) -> None:
    """Head can be reached, fully reverted (tables and trigger function) and reached again."""
    alembic_config = build_alembic_config(scratch_schema_connection)
    command.upgrade(alembic_config, "head")
    assert _scratch_table_names(scratch_schema_connection) == {
        *APPLICATION_TABLES,
        "alembic_version",
    }
    command.downgrade(alembic_config, "base")
    assert _scratch_table_names(scratch_schema_connection) == {"alembic_version"}
    assert _scratch_guard_function_count(scratch_schema_connection) == 0
    command.upgrade(alembic_config, "head")
    assert _scratch_table_names(scratch_schema_connection) >= APPLICATION_TABLES
    assert _scratch_guard_function_count(scratch_schema_connection) == 1


def test_migrated_schema_matches_the_orm_models(database_connection: Connection) -> None:
    """Autogenerate finds no difference between the migration and the models."""
    migration_context = MigrationContext.configure(database_connection)
    assert compare_metadata(migration_context, Base.metadata) == []


def test_audit_event_has_indexes_on_type_subject_and_time(
    database_connection: Connection,
) -> None:
    """Every audit_event column used in a WHERE or ORDER BY is indexed."""
    indexed_columns = {
        index["name"]: index["column_names"]
        for index in inspect(database_connection).get_indexes("audit_event")
    }
    assert indexed_columns == {
        "ix_audit_event_event_type": ["event_type"],
        "ix_audit_event_subject_type_subject_id": ["subject_type", "subject_id"],
        "ix_audit_event_occurred_at": ["occurred_at"],
    }


def test_payment_attempt_lookup_columns_are_unique_and_therefore_indexed(
    database_connection: Connection,
) -> None:
    """order_id and idempotency_key each carry a unique constraint, which PostgreSQL indexes."""
    unique_constraints = {
        constraint["name"]: constraint["column_names"]
        for constraint in inspect(database_connection).get_unique_constraints("payment_attempt")
    }
    assert unique_constraints == {
        "uq_payment_attempt_order_id": ["order_id"],
        "uq_payment_attempt_idempotency_key": ["idempotency_key"],
    }


@pytest.mark.parametrize(
    ("table_name", "expected_check_constraint_names"),
    [
        (
            "payment_attempt",
            {
                "ck_payment_attempt_amount_in_paise_positive",
                "ck_payment_attempt_status_known",
                "ck_payment_attempt_request_fingerprint_length",
                "ck_payment_attempt_failure_code_known",
            },
        ),
        ("audit_event", {"ck_audit_event_event_type_known"}),
        ("merchant", {"ck_merchant_failed_pin_attempt_count_not_negative"}),
        ("device_pairing", {"ck_device_pairing_access_token_hash_length"}),
        ("product", {"ck_product_list_price_in_paise_positive"}),
    ],
)
def test_check_constraints_exist_with_convention_names(
    database_connection: Connection, table_name: str, expected_check_constraint_names: set[str]
) -> None:
    """Status, event type, positive paise and fingerprint length are enforced by the database."""
    check_constraint_names = {
        constraint["name"]
        for constraint in inspect(database_connection).get_check_constraints(table_name)
    }
    assert check_constraint_names == expected_check_constraint_names


def test_tables_hold_money_as_bigint_paise_and_no_card_fields(
    database_connection: Connection,
) -> None:
    """Money is BIGINT paise only, audit_event has no updated_at, and no column is card data."""
    database_inspector = inspect(database_connection)
    payment_attempt_columns = {
        column["name"]: column for column in database_inspector.get_columns("payment_attempt")
    }
    audit_event_column_names = {
        column["name"] for column in database_inspector.get_columns("audit_event")
    }
    assert str(payment_attempt_columns["amount_in_paise"]["type"]) == "BIGINT"
    assert "updated_at" not in audit_event_column_names
    for column_name in {*payment_attempt_columns, *audit_event_column_names}:
        assert not any(card_word in column_name for card_word in CARD_FIELD_WORDS)


def _scratch_payment_attempt_column_names(connection: Connection) -> set[str]:
    """Lists the payment_attempt columns currently in the scratch schema."""
    return {
        column["name"]
        for column in inspect(connection).get_columns("payment_attempt", schema=SCRATCH_SCHEMA)
    }


def test_migration_0002_adds_and_removes_the_failure_code_column(
    scratch_schema_connection: Connection,
) -> None:
    """0002 adds the nullable failure_code with its check; downgrading to 0001 removes both."""
    alembic_config = build_alembic_config(scratch_schema_connection)
    command.upgrade(alembic_config, "0001")
    assert "failure_code" not in _scratch_payment_attempt_column_names(scratch_schema_connection)
    command.upgrade(alembic_config, "0002")
    failure_code_column = next(
        column
        for column in inspect(scratch_schema_connection).get_columns(
            "payment_attempt", schema=SCRATCH_SCHEMA
        )
        if column["name"] == "failure_code"
    )
    assert failure_code_column["nullable"] is True
    check_constraint_names = {
        constraint["name"]
        for constraint in inspect(scratch_schema_connection).get_check_constraints(
            "payment_attempt", schema=SCRATCH_SCHEMA
        )
    }
    assert "ck_payment_attempt_failure_code_known" in check_constraint_names
    command.downgrade(alembic_config, "0001")
    assert "failure_code" not in _scratch_payment_attempt_column_names(scratch_schema_connection)


@pytest.mark.parametrize("table_name", ["device_pairing", "product"])
def test_merchant_foreign_keys_are_indexed(
    database_connection: Connection, table_name: str
) -> None:
    """Every foreign key is indexed (backend.md section 8); each points at merchant.id."""
    database_inspector = inspect(database_connection)
    foreign_keys = database_inspector.get_foreign_keys(table_name)
    assert [
        (foreign_key["constrained_columns"], foreign_key["referred_table"])
        for foreign_key in foreign_keys
    ] == [(["merchant_id"], "merchant")]
    indexed_columns = [
        index["column_names"] for index in database_inspector.get_indexes(table_name)
    ]
    assert ["merchant_id"] in indexed_columns


@pytest.mark.parametrize(
    ("table_name", "expected_unique_constraints"),
    [
        ("merchant", {"uq_merchant_shop_code": ["shop_code"]}),
        ("device_pairing", {"uq_device_pairing_access_token_hash": ["access_token_hash"]}),
        ("product", {}),
    ],
)
def test_merchant_lookup_columns_are_unique(
    database_connection: Connection,
    table_name: str,
    expected_unique_constraints: dict[str, list[str]],
) -> None:
    """Shop codes and token hashes are unique, which also indexes the sign-in lookups."""
    unique_constraints = {
        constraint["name"]: constraint["column_names"]
        for constraint in inspect(database_connection).get_unique_constraints(table_name)
    }
    assert unique_constraints == expected_unique_constraints


def test_merchant_tables_hold_no_pin_token_card_or_customer_fields(
    database_connection: Connection,
) -> None:
    """Only PIN and token hashes are stored, prices are BIGINT paise and no card field exists."""
    database_inspector = inspect(database_connection)
    columns_by_table = {
        table_name: {
            column["name"]: column for column in database_inspector.get_columns(table_name)
        }
        for table_name in MERCHANT_TABLES
    }
    assert {"pin_hash", "pin_salt"} <= set(columns_by_table["merchant"])
    assert "pin" not in columns_by_table["merchant"]
    assert "access_token" not in columns_by_table["device_pairing"]
    assert str(columns_by_table["product"]["list_price_in_paise"]["type"]) == "BIGINT"
    for table_name, columns in columns_by_table.items():
        assert {"id", "created_at", "updated_at"} <= set(columns), table_name
        for column_name in columns:
            assert not any(card_word in column_name for card_word in CARD_FIELD_WORDS), column_name


def test_migration_0003_creates_and_removes_the_merchant_tables(
    scratch_schema_connection: Connection,
) -> None:
    """0003 adds merchant, device_pairing and product; downgrading to 0002 removes all three."""
    alembic_config = build_alembic_config(scratch_schema_connection)
    command.upgrade(alembic_config, "0002")
    assert not set(MERCHANT_TABLES) & _scratch_table_names(scratch_schema_connection)
    command.upgrade(alembic_config, "0003")
    assert set(MERCHANT_TABLES) <= _scratch_table_names(scratch_schema_connection)
    command.downgrade(alembic_config, "0002")
    assert not set(MERCHANT_TABLES) & _scratch_table_names(scratch_schema_connection)
    assert {"payment_attempt", "audit_event"} <= _scratch_table_names(scratch_schema_connection)
