"""A Clock test double whose time only moves when a test moves it."""

from datetime import datetime, timedelta


class FixedClock:
    """Clock that returns a set moment, so stored timestamps are predictable in tests."""

    def __init__(self, current_moment: datetime) -> None:
        """Starts the clock at a timezone-aware moment."""
        self._current_moment = current_moment

    def now(self) -> datetime:
        """Returns the moment the test last set."""
        return self._current_moment

    def advance(self, duration: timedelta) -> None:
        """Moves the clock forward by a duration."""
        self._current_moment += duration
