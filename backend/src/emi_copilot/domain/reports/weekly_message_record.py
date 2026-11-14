"""WeeklyMessageSentRecord: when a shop's weekly message was marked sent, and whether just now."""

from dataclasses import dataclass
from datetime import datetime


# Pattern: Value Object. The outcome of marking one week's message sent, exactly once.
@dataclass(frozen=True, slots=True)
class WeeklyMessageSentRecord:
    """The stored sent moment; was_sent_now is False when an earlier send already recorded it."""

    sent_at: datetime
    was_sent_now: bool
