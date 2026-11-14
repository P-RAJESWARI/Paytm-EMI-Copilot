"""Records, once per shop and week, that the weekly message was sent; reads that moment back."""

from datetime import UTC, date, datetime

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from emi_copilot.core.clock import Clock
from emi_copilot.domain.reports.weekly_message_record import WeeklyMessageSentRecord
from emi_copilot.models import WeeklyMessageModel


def _select_sent_at(merchant_id: str, period_start_date: date) -> Select[datetime]:
    """Selects the sent moment of one shop's message for one week."""
    return select(WeeklyMessageModel.sent_at).where(
        (WeeklyMessageModel.merchant_id == merchant_id)
        & (WeeklyMessageModel.period_start_date == period_start_date)
    )


# Pattern: Repository. The weekly message's sent state; the unique key makes sending idempotent.
class WeeklyMessageRepository:
    """Finds and records the sent moment of one shop's weekly message for one week."""

    def __init__(self, session: Session, clock: Clock) -> None:
        """Uses the unit of work's session and the injected clock for the row timestamps."""
        self._session = session
        self._clock = clock

    def find_sent_at(self, merchant_id: str, period_start_date: date) -> datetime | None:
        """Gives when the week's message was sent, or None while it has not been."""
        sent_at = self._session.scalars(
            _select_sent_at(merchant_id, period_start_date)
        ).one_or_none()
        return None if sent_at is None else sent_at.astimezone(UTC)

    def record_sent_once(
        self, weekly_message_id: str, merchant_id: str, period_start_date: date, sent_at: datetime
    ) -> WeeklyMessageSentRecord:
        """Stores the sent moment unless one is stored; a racing second send keeps the first.

        INSERT ... ON CONFLICT DO NOTHING on the (merchant, week) key, so two concurrent sends
        cannot both record, and the loser reads the winner's moment.
        """
        now = self._clock.now()
        inserted_sent_at = self._session.execute(
            insert(WeeklyMessageModel)
            .values(
                id=weekly_message_id,
                merchant_id=merchant_id,
                period_start_date=period_start_date,
                sent_at=sent_at,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=["merchant_id", "period_start_date"])
            .returning(WeeklyMessageModel.sent_at)
        ).scalar_one_or_none()
        if inserted_sent_at is not None:
            return WeeklyMessageSentRecord(inserted_sent_at.astimezone(UTC), was_sent_now=True)
        stored_sent_at = self._session.scalars(
            _select_sent_at(merchant_id, period_start_date)
        ).one()
        return WeeklyMessageSentRecord(stored_sent_at.astimezone(UTC), was_sent_now=False)
