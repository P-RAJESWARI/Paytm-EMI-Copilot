"""Injectable generator of opaque identifiers so tests can stay deterministic."""

from typing import Protocol

from ulid import ULID


class IdGenerator(Protocol):
    """Anything that can produce a new opaque, unique string identifier."""

    def new_id(self) -> str:
        """Returns a new identifier that has not been returned before."""
        ...


class UlidIdGenerator:
    """IdGenerator producing time-sortable 26-character ULID strings."""

    def new_id(self) -> str:
        """Returns a fresh ULID in its canonical Crockford base32 form."""
        return str(ULID())
