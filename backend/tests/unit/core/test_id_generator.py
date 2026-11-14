"""Tests for the injectable ID generator."""

from ulid import ULID

from emi_copilot.core.id_generator import IdGenerator, UlidIdGenerator


def test_ulid_id_generator_new_id_returns_canonical_ulid_string() -> None:
    """Generated IDs are 26-character ULIDs that round-trip through the ULID parser."""
    generated_id = UlidIdGenerator().new_id()
    assert len(generated_id) == 26
    assert str(ULID.from_str(generated_id)) == generated_id


def test_ulid_id_generator_new_id_returns_a_different_id_each_call() -> None:
    """Every call yields a fresh identifier."""
    id_generator: IdGenerator = UlidIdGenerator()
    generated_ids = {id_generator.new_id() for _ in range(1000)}
    assert len(generated_ids) == 1000
