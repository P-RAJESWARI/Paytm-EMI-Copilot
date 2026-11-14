"""Tests for random bearer tokens that are stored only as their SHA-256 hash."""

import re

from emi_copilot.core.opaque_token import (
    TOKEN_HASH_HEX_LENGTH,
    hash_opaque_token,
    issue_opaque_token,
)

URL_SAFE_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")
SYNTHETIC_BEARER_VALUE = "synthetic-opaque-token-for-tests"  # pragma: allowlist secret
SYNTHETIC_VALUE_SHA256_HEX = (
    "8a5094b88b623f70b98e776b79c7f7e9bcdbe3d2e8aae7036df9ea38134ea485"  # pragma: allowlist secret
)


def test_hash_opaque_token_with_known_token_gives_its_sha256_hex() -> None:
    """The stored form is the plain lowercase hex SHA-256 of the token's UTF-8 bytes."""
    assert hash_opaque_token(SYNTHETIC_BEARER_VALUE) == SYNTHETIC_VALUE_SHA256_HEX


def test_issue_opaque_token_gives_url_safe_256_bit_token_with_matching_hash() -> None:
    """A token is 32 random bytes in URL-safe base64 and arrives with its own hash."""
    issued_token = issue_opaque_token()
    assert URL_SAFE_TOKEN_PATTERN.fullmatch(issued_token.token)
    assert issued_token.token_hash == hash_opaque_token(issued_token.token)
    assert len(issued_token.token_hash) == TOKEN_HASH_HEX_LENGTH


def test_issue_opaque_token_called_repeatedly_never_repeats_a_token() -> None:
    """Each call draws fresh randomness."""
    issued_tokens = {issue_opaque_token().token for _ in range(100)}
    assert len(issued_tokens) == 100
