"""An in-memory fixed-window rate limiter that reads time from the injected clock.

One instance is built by the composition root and kept on the application components, never in
a module global. Counts live in this process only, which suits the single-process demo server.
"""

import math
import threading
from dataclasses import dataclass
from datetime import timedelta

from emi_copilot.core.clock import Clock

# Above this many tracked keys, keys whose window has ended are dropped, so memory grows only
# with the distinct keys seen in one window.
DEFAULT_MAXIMUM_TRACKED_KEY_COUNT = 10_000


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Whether one request may go ahead and, if not, how many whole seconds until it may."""

    is_allowed: bool
    retry_after_in_seconds: int


@dataclass(frozen=True, slots=True)
class _WindowCount:
    """How many requests one key has made in the window that starts at the given index."""

    window_index: int
    request_count: int


class FixedWindowRateLimiter:
    """Allows at most N requests per key in each fixed window of time, such as 10 a minute.

    Windows are aligned to the Unix epoch, so every key's window ends at the same moments; the
    window index is the number of whole windows since the epoch.
    """

    def __init__(
        self,
        clock: Clock,
        maximum_requests_per_window: int,
        window_duration: timedelta,
        maximum_tracked_key_count: int = DEFAULT_MAXIMUM_TRACKED_KEY_COUNT,
    ) -> None:
        """Keeps the clock and the limits; both limits must be positive."""
        if maximum_requests_per_window < 1:
            raise ValueError("At least one request per window must be allowed.")
        if window_duration <= timedelta(0):
            raise ValueError("The window duration must be positive.")
        self._clock = clock
        self._maximum_requests_per_window = maximum_requests_per_window
        self._window_duration_in_seconds = window_duration.total_seconds()
        self._maximum_tracked_key_count = maximum_tracked_key_count
        self._window_counts_by_key: dict[str, _WindowCount] = {}
        self._lock = threading.Lock()

    @property
    def tracked_key_count(self) -> int:
        """Gives how many keys hold a count now, so memory use can be watched."""
        with self._lock:
            return len(self._window_counts_by_key)

    def try_acquire(self, key: str) -> RateLimitDecision:
        """Counts one request for the key if it is under the limit in the current window."""
        current_timestamp = self._clock.now().timestamp()
        window_index = math.floor(current_timestamp / self._window_duration_in_seconds)
        with self._lock:
            self._forget_finished_windows_when_full(window_index)
            stored_count = self._window_counts_by_key.get(key)
            request_count = (
                stored_count.request_count
                if stored_count is not None and stored_count.window_index == window_index
                else 0
            )
            if request_count >= self._maximum_requests_per_window:
                return RateLimitDecision(
                    is_allowed=False,
                    retry_after_in_seconds=self._seconds_until_window_ends(
                        window_index, current_timestamp
                    ),
                )
            self._window_counts_by_key[key] = _WindowCount(window_index, request_count + 1)
        return RateLimitDecision(is_allowed=True, retry_after_in_seconds=0)

    def _seconds_until_window_ends(self, window_index: int, current_timestamp: float) -> int:
        """Gives the whole seconds, at least one, until the next window starts."""
        window_end_timestamp = (window_index + 1) * self._window_duration_in_seconds
        return max(1, math.ceil(window_end_timestamp - current_timestamp))

    def _forget_finished_windows_when_full(self, current_window_index: int) -> None:
        """Drops every key whose window has ended once too many keys are tracked."""
        if len(self._window_counts_by_key) < self._maximum_tracked_key_count:
            return
        self._window_counts_by_key = {
            key: window_count
            for key, window_count in self._window_counts_by_key.items()
            if window_count.window_index == current_window_index
        }
