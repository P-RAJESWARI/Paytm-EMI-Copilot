"""Integration tests for migration 0006: customer sessions, OTP challenges and consent records."""

from collections.abc import Iterator

import pytest
from alembic import command
from sqlalchemy import Connection, Engine, inspect, text

from tests.integration.migration_runner import build_alembic_config

pytestmark = pytest.mark.integration

SCRATCH_SCHEMA = "customer_flow_migration_scratch"
CUSTOMER_FLOW_TABLES = {"customer_session", "consent_otp_challenge", "consent_record"}
CUSTOMER_FLOW_AUDIT_TYPES = (
    "CUSTOMER_SESSION_STARTED",
    "OTP_VERIFICATION_FAILED",
    "CONSENT_RECORDED",
)
INSERT_CONSENT_AUDIT_ROW = (
    "INSERT INTO audit_event VALUES ('01JCAUDITSCRATCH0000000001', 'CONSENT_RECORDED',"
    " 'consent_record', '01JCCONSENT000000000000001', NULL, now(), '{}'::jsonb, now())"
)
# Words a column must never carry: plain secrets, personal data and card fields.
FORBIDDEN_COLUMN_WORDS = ("card", "cvv", "expiry", "income", "phone_number", "otp_code", "token")


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


def test_migration_0006_creates_and_removes_the_customer_flow_tables(
    scratch_schema_connection: Connection,
) -> None:
    """0006 adds the three tables; going back to 0005 drops them and their triggers."""
    alembic_config = build_alembic_config(scratch_schema_connection)
    command.upgrade(alembic_config, "0005")
    assert not CUSTOMER_FLOW_TABLES & _table_names(scratch_schema_connection)
    command.upgrade(alembic_config, "0006")
    assert _table_names(scratch_schema_connection) >= CUSTOMER_FLOW_TABLES
    command.downgrade(alembic_config, "0005")
    assert not CUSTOMER_FLOW_TABLES & _table_names(scratch_schema_connection)
    command.upgrade(alembic_config, "head")


def test_migration_0006_downgrade_keeps_consent_audit_rows_it_cannot_delete(
    scratch_schema_connection: Connection,
) -> None:
    """audit_event is append-only, so the restored type check is NOT VALID and the row survives."""
    alembic_config = build_alembic_config(scratch_schema_connection)
    command.upgrade(alembic_config, "0006")
    scratch_schema_connection.execute(text(INSERT_CONSENT_AUDIT_ROW))
    command.downgrade(alembic_config, "0005")
    remaining_rows = scratch_schema_connection.execute(
        text("SELECT count(*) FROM audit_event WHERE event_type = 'CONSENT_RECORDED'")
    ).scalar_one()
    assert remaining_rows == 1


@pytest.mark.parametrize(
    ("table_name", "foreign_key_column"),
    [
        ("customer_session", "sale_id"),
        ("consent_otp_challenge", "customer_session_id"),
        ("consent_record", "sale_id"),
        ("consent_record", "customer_session_id"),
    ],
)
def test_every_customer_flow_foreign_key_leads_an_index(
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


@pytest.mark.parametrize(
    ("table_name", "expected_unique_constraints"),
    [
        ("customer_session", {"uq_customer_session_token_hash": ["token_hash"]}),
        ("consent_otp_challenge", {}),
        (
            "consent_record",
            {
                "uq_consent_record_sale_id": ["sale_id"],
                "uq_consent_record_chain_position": ["chain_position"],
                "uq_consent_record_previous_record_hash": ["previous_record_hash"],
                "uq_consent_record_record_hash": ["record_hash"],
            },
        ),
    ],
)
def test_customer_flow_unique_keys(
    database_connection: Connection,
    table_name: str,
    expected_unique_constraints: dict[str, list[str]],
) -> None:
    """Token hashes are unique; one consent per sale; the chain cannot fork."""
    unique_constraints = {
        constraint["name"]: constraint["column_names"]
        for constraint in inspect(database_connection).get_unique_constraints(table_name)
    }
    assert unique_constraints == expected_unique_constraints


@pytest.mark.parametrize(
    ("table_name", "expected_check_constraint_names"),
    [
        (
            "customer_session",
            {
                "ck_customer_session_token_hash_length",
                "ck_customer_session_monthly_budget_in_paise_positive",
                "ck_customer_session_comfort_check_status_known",
                "ck_customer_session_language_known",
                "ck_customer_session_expires_after_start",
            },
        ),
        (
            "consent_otp_challenge",
            {
                "ck_consent_otp_challenge_code_hash_length",
                "ck_consent_otp_challenge_attempts_remaining_not_negative",
            },
        ),
        (
            "consent_record",
            {
                "ck_consent_record_chain_position_positive",
                "ck_consent_record_genesis_link_only_first",
                "ck_consent_record_phone_last_two_digits_only",
                "ck_consent_record_language_known",
            },
        ),
    ],
)
def test_customer_flow_check_constraints_exist_with_convention_names(
    database_connection: Connection, table_name: str, expected_check_constraint_names: set[str]
) -> None:
    """Statuses, languages, positive paise and the genesis link are enforced by the database."""
    check_constraint_names = {
        constraint["name"]
        for constraint in inspect(database_connection).get_check_constraints(table_name)
    }
    assert check_constraint_names == expected_check_constraint_names


def test_customer_flow_tables_hold_hashes_and_paise_only(database_connection: Connection) -> None:
    """Budget is BIGINT paise; consent_record has no updated_at; no plain secret or card column."""
    database_inspector = inspect(database_connection)
    columns_by_table = {
        table_name: {
            column["name"]: column for column in database_inspector.get_columns(table_name)
        }
        for table_name in CUSTOMER_FLOW_TABLES
    }
    assert str(columns_by_table["customer_session"]["monthly_budget_in_paise"]["type"]) == "BIGINT"
    assert "updated_at" not in columns_by_table["consent_record"]
    assert {"token_hash"} <= set(columns_by_table["customer_session"])
    assert {"code_hash"} <= set(columns_by_table["consent_otp_challenge"])
    assert {"phone_hash", "phone_last_two_digits"} <= set(columns_by_table["consent_record"])
    for table_name, columns in columns_by_table.items():
        assert {"id", "created_at"} <= set(columns), table_name
        for column_name in columns:
            assert not any(word in column_name for word in FORBIDDEN_COLUMN_WORDS) or (
                column_name == "token_hash"
            ), column_name


def test_audit_event_accepts_the_customer_flow_event_types(database_connection: Connection) -> None:
    """The type check lists the three customer flow types beside the earlier ones."""
    check_definition = database_connection.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint"
            " WHERE conname = 'ck_audit_event_event_type_known'"
        )
    ).scalar_one()
    for event_type in (*CUSTOMER_FLOW_AUDIT_TYPES, "SALE_PAYMENT_OUTCOME_IGNORED"):
        assert event_type in check_definition
