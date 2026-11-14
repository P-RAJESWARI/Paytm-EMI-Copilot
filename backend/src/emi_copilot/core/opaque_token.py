"""Random bearer tokens that are stored only as their SHA-256 hash.

The token itself is shown once, to the device that asked for it. The database keeps only the
hash, so a read of the table cannot be replayed as a login.
"""

import hashlib
import secrets
from dataclasses import dataclass

TOKEN_ENTROPY_IN_BYTES = 32
TOKEN_HASH_HEX_LENGTH = 64


@dataclass(frozen=True, slots=True)
class IssuedOpaqueToken:
    """A newly drawn token and the hash to store for it; the token is never stored or logged."""

    token: str
    token_hash: str


def hash_opaque_token(token: str) -> str:
    """Gives the lowercase hex SHA-256 of a token, the only form in which it is stored."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_opaque_token() -> IssuedOpaqueToken:
    """Draws a URL-safe token with 256 bits of entropy and pairs it with its hash."""
    token = secrets.token_urlsafe(TOKEN_ENTROPY_IN_BYTES)
    return IssuedOpaqueToken(token=token, token_hash=hash_opaque_token(token))
