"""Injectable source of the current time so tests can stay deterministic."""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Anything that can tell the current time as a timezone-aware UTC datetime."""

    def now(self) -> datetime:
        """Returns the current moment as a timezone-aware UTC datetime."""
        ...


class SystemClock:
    """Clock backed by the operating system's wall clock."""

    def now(self) -> datetime:
        """Returns the operating system's current time in UTC."""
        return datetime.now(UTC)
