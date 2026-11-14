"""The delivery Mock announces itself, sends nothing and never logs the message text."""

import logging
from datetime import date

import pytest

from emi_copilot.adapters.weekly_message_delivery.factory import WeeklyMessageDeliveryFactory
from emi_copilot.adapters.weekly_message_delivery.mock_adapter import (
    MOCK_DELIVERY_ACTIVE_WARNING,
    MockWeeklyMessageDeliveryAdapter,
)
from emi_copilot.domain.reports.weekly_message_record import WeeklyMessageDelivery
from emi_copilot.domain.reports.weekly_message_template import WeeklyMessages, WeeklyMessageText

MESSAGE_SENTENCE = "44 of 120 customers bought on EMI."


def test_delivery_factory_builds_the_mock_and_it_warns_at_startup(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Only the labelled Mock exists (plan Q14)."""
    with caplog.at_level(logging.WARNING):
        adapter = WeeklyMessageDeliveryFactory().create()
    assert isinstance(adapter, MockWeeklyMessageDeliveryAdapter)
    assert adapter.adapter_name == "mock"
    assert [record.getMessage() for record in caplog.records] == [MOCK_DELIVERY_ACTIVE_WARNING]


def test_mock_delivery_logs_the_shop_and_week_but_never_the_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Log events, not payloads (backend.md section 10)."""
    adapter = MockWeeklyMessageDeliveryAdapter()
    text = WeeklyMessageText(title="Your EMI sales", paragraphs=(MESSAGE_SENTENCE,))
    with caplog.at_level(logging.INFO):
        adapter.deliver_weekly_message(
            WeeklyMessageDelivery(
                merchant_id="01JCMERCHANT00000000000001",
                period_start_date=date(2026, 11, 9),
                messages=WeeklyMessages(english=text, tamil=text),
            )
        )
    (record,) = [record for record in caplog.records if record.levelno == logging.INFO]
    assert record.getMessage() == "weekly message delivery simulated"
    assert record.__dict__["period_start_date"] == "2026-11-09"
    assert MESSAGE_SENTENCE not in str(record.__dict__)
