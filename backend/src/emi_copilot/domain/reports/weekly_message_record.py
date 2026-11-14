"""The weekly message's sent record, and the delivery handed to the port that sends it."""

from dataclasses import dataclass
from datetime import date, datetime

from emi_copilot.domain.reports.weekly_message_template import WeeklyMessages


# Pattern: Value Object. The outcome of marking one week's message sent, exactly once.
@dataclass(frozen=True, slots=True)
class WeeklyMessageSentRecord:
    """The stored sent moment; was_sent_now is False when an earlier send already recorded it."""

    sent_at: datetime
    was_sent_now: bool


@dataclass(frozen=True, slots=True)
class WeeklyMessageDelivery:
    """One shop's weekly message for one week, handed to the delivery port to send."""

    merchant_id: str
    period_start_date: date
    messages: WeeklyMessages
