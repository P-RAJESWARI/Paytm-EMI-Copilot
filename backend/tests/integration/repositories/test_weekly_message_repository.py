"""Integration tests for WeeklyMessageRepository: sent once per shop and week."""

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.reports.weekly_message_record import WeeklyMessageSentRecord
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.fixed_clock import FixedClock
from tests.merchant_builders import MERCHANT_ID, OTHER_MERCHANT_ID, build_merchant
from tests.payment_builders import CREATED_AT

pytestmark = pytest.mark.integration

WEEK_START = date(2026, 11, 9)


def test_record_sent_once_keeps_the_first_moment_per_shop_and_week(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """A second send of the same week keeps the first moment; another shop or week is separate."""
    later = CREATED_AT + timedelta(minutes=5)
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        unit_of_work.merchants.add(build_merchant())
        unit_of_work.merchants.add(build_merchant(id=OTHER_MERCHANT_ID, shop_code="SHOP-0002"))
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        assert unit_of_work.weekly_messages.find_sent_at(MERCHANT_ID, WEEK_START) is None
        first = unit_of_work.weekly_messages.record_sent_once(
            "01JCWEEKLYMESSAGE000000001", MERCHANT_ID, WEEK_START, CREATED_AT
        )
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        second = unit_of_work.weekly_messages.record_sent_once(
            "01JCWEEKLYMESSAGE000000002", MERCHANT_ID, WEEK_START, later
        )
        other_shop = unit_of_work.weekly_messages.record_sent_once(
            "01JCWEEKLYMESSAGE000000003", OTHER_MERCHANT_ID, WEEK_START, later
        )
        stored = unit_of_work.weekly_messages.find_sent_at(MERCHANT_ID, WEEK_START)
        next_week = unit_of_work.weekly_messages.find_sent_at(
            MERCHANT_ID, WEEK_START + timedelta(days=7)
        )
    assert first == WeeklyMessageSentRecord(CREATED_AT, was_sent_now=True)
    assert second == WeeklyMessageSentRecord(CREATED_AT, was_sent_now=False)
    assert other_shop == WeeklyMessageSentRecord(later, was_sent_now=True)
    assert (stored, next_week) == (CREATED_AT, None)
