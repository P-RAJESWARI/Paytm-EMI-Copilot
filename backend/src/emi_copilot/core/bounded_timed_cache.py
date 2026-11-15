"""BoundedTimedCache: a small in-memory cache whose entries expire and whose size is capped.

One instance is built by the composition root and kept on the application components, never in
a module global. Entries live in this process only, which suits the single-process demo server.
"""

import threading
from collections import OrderedDict
from collections.abc import Hashable
from dataclasses import dataclass
from datetime import datetime, timedelta

from emi_copilot.core.clock import Clock


@dataclass(frozen=True, slots=True)
class _TimedEntry[ValueType]:
    """One cached value and the moment it was stored."""

    value: ValueType
    stored_at: datetime


class BoundedTimedCache[KeyType: Hashable, ValueType]:
    """Keeps at most maximum_entries values, each for lifetime; the oldest stored is dropped first.

    Time comes from the injected Clock, so expiry is deterministic in tests. Thread-safe, because
    FastAPI runs synchronous endpoints on a thread pool.
    """

    def __init__(self, clock: Clock, maximum_entries: int, lifetime: timedelta) -> None:
        """Keeps the clock, the size cap and how long an entry stays usable."""
        self._clock = clock
        self._maximum_entries = maximum_entries
        self._lifetime = lifetime
        self._entries: OrderedDict[KeyType, _TimedEntry[ValueType]] = OrderedDict()
        self._lock = threading.Lock()

    def find(self, key: KeyType) -> ValueType | None:
        """Gives the value stored under the key, or None when there is none or it has expired."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if self._clock.now() - entry.stored_at >= self._lifetime:
                del self._entries[key]
                return None
            return entry.value

    def store(self, key: KeyType, value: ValueType) -> None:
        """Stores the value as the newest entry, dropping the oldest entries beyond the cap."""
        with self._lock:
            self._entries.pop(key, None)
            self._entries[key] = _TimedEntry(value, self._clock.now())
            while len(self._entries) > self._maximum_entries:
                self._entries.popitem(last=False)
