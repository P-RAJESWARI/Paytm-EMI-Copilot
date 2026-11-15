"""Shown-text caches: a repeat explanation costs no AI call; weekly text is stable per facts."""

import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import override

import pytest

from emi_copilot.core.bounded_timed_cache import BoundedTimedCache
from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.money import Money
from emi_copilot.domain.reports.weekly_message_template import WeeklyMessageTemplate
from emi_copilot.domain.reports.weekly_message_wording import MessageLanguage
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.services.ai.ai_flow_types import AiTextSource
from emi_copilot.services.ai.ai_usage_logger import AiUsageLogger
from emi_copilot.services.ai.audited_explanation_service import AuditedExplanationService
from emi_copilot.services.ai.audited_weekly_message_writer import (
    AuditedWeeklyMessageWriter,
    build_weekly_message_cache,
)
from emi_copilot.services.ai.shown_explanation_cache import ShownExplanationCache
from emi_copilot.services.customer.customer_explanation_service import CustomerExplanationService
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.customer.session_plan_finder import SessionPlanFinder
from emi_copilot.services.customer.template_explanation_service import TemplateExplanationService
from tests.ai_flow_builders import (
    TEST_AI_PRICE_LIST,
    WEEKLY_ENGLISH_AI_TEXT,
    build_explanation_flow,
    build_weekly_message_flow,
    build_weekly_message_writer,
    render_weekly_template,
)
from tests.fakes.scripted_explanation_text_port import ScriptedExplanationTextPort
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.report_builders import build_design_weekly_message_facts
from tests.sale_builders import build_no_cost_chosen_plan
from tests.unit.services.ai.test_audited_explanation_service import (
    FailingFlowRunner,
    read_usage_outcomes,
)

MOMENT = datetime(2026, 11, 15, 9, 30, tzinfo=UTC)
PASSING_TEXT = (
    "No-cost EMI from Brand: you pay ₹3,667 each month for 6 months. "
    "The extra you pay in total is ₹0."
)
SESSION_ID = "01JCSESSION0000000000000001"
OTHER_SESSION_ID = "01JCSESSION0000000000000002"
MERCHANT_ID = "01JCMERCHANTRAVI0000000001"
SESSION_TOKEN = "synthetic-session-token"  # noqa: S105 - a synthetic test value


class FixedPlanFinder(SessionPlanFinder):
    """Gives one plan for any session and offer, without a database."""

    def __init__(self, plan: ChosenPlan) -> None:
        """Keeps the plan to give; the database collaborators are not needed."""
        self.plan = plan

    @override
    def find_plan(self, credentials: CustomerSessionCredentials, offer_id: str) -> ChosenPlan:
        """Gives the fixed plan."""
        return self.plan


def credentials(session_id: str = SESSION_ID) -> CustomerSessionCredentials:
    """Credentials of a test session."""
    return CustomerSessionCredentials(customer_session_id=session_id, session_token=SESSION_TOKEN)


def build_explanation_service(
    port: ScriptedExplanationTextPort, clock: FixedClock
) -> tuple[CustomerExplanationService, FixedPlanFinder, ShownExplanationCache]:
    """Wires the customer explanation over the audited explainer and a fresh cache."""
    plan_finder = FixedPlanFinder(build_no_cost_chosen_plan())
    cache = ShownExplanationCache(clock)
    explainer = AuditedExplanationService(
        build_explanation_flow(port),
        TemplateExplanationService(format_paise_as_whole_rupees),
        AiUsageLogger(TEST_AI_PRICE_LIST),
    )
    service = CustomerExplanationService(plan_finder, explainer, cache, SequentialIdGenerator())
    return service, plan_finder, cache


def test_customer_explanation_cache_hit_does_not_call_the_port_twice() -> None:
    """The same session, plan and language get the same text and id from one AI call."""
    port = ScriptedExplanationTextPort({CustomerLanguage.ENGLISH: PASSING_TEXT})
    service, _, cache = build_explanation_service(port, FixedClock(MOMENT))
    first = service.explain_for_session(credentials(), "offer", CustomerLanguage.ENGLISH)
    second = service.explain_for_session(credentials(), "offer", CustomerLanguage.ENGLISH)
    assert second == first
    assert len(port.received_requests) == 1
    assert cache.find_by_explanation_id(SESSION_ID, first.explanation_id) == first
    assert cache.find_by_explanation_id(OTHER_SESSION_ID, first.explanation_id) is None


def test_customer_explanation_cache_misses_for_another_session_changed_figures_or_expiry() -> None:
    """Another session, new figures or an expired entry each make a fresh explanation."""
    port = ScriptedExplanationTextPort({CustomerLanguage.ENGLISH: PASSING_TEXT})
    clock = FixedClock(MOMENT)
    service, plan_finder, cache = build_explanation_service(port, clock)
    first = service.explain_for_session(credentials(), "offer", CustomerLanguage.ENGLISH)
    service.explain_for_session(credentials(OTHER_SESSION_ID), "offer", CustomerLanguage.ENGLISH)
    plan_finder.plan = replace(plan_finder.plan, monthly_installment=Money.from_rupees("3666.66"))
    service.explain_for_session(credentials(), "offer", CustomerLanguage.ENGLISH)
    clock.advance(timedelta(minutes=31))
    assert cache.find_by_explanation_id(SESSION_ID, first.explanation_id) is None
    assert len(port.received_requests) == 3


def test_bounded_timed_cache_drops_the_oldest_entry_beyond_its_cap() -> None:
    """With a cap of two, storing a third value forgets the first."""
    cache: BoundedTimedCache[str, int] = BoundedTimedCache(
        FixedClock(MOMENT), 2, timedelta(minutes=1)
    )
    for value, key in enumerate(("first", "second", "third")):
        cache.store(key, value)
    assert (cache.find("first"), cache.find("second"), cache.find("third")) == (None, 1, 2)


def test_audited_weekly_message_writer_falls_back_per_language_and_repeats_shown_text() -> None:
    """English passes, Tamil is unavailable: Tamil is the template; a repeat makes no AI call."""
    port = ScriptedExplanationTextPort({CustomerLanguage.ENGLISH: WEEKLY_ENGLISH_AI_TEXT})
    writer = build_weekly_message_writer(FixedClock(MOMENT), port)
    facts = build_design_weekly_message_facts()
    written = writer.write(MERCHANT_ID, facts)
    assert (written.english_source, written.tamil_source) == (
        AiTextSource.AI_AUDITED,
        AiTextSource.TEMPLATE,
    )
    assert written.messages.english.paragraphs == (WEEKLY_ENGLISH_AI_TEXT,)
    assert written.messages.tamil == render_weekly_template(MessageLanguage.TAMIL, facts)
    request_count = len(port.received_requests)
    assert writer.write(MERCHANT_ID, facts) == written
    assert len(port.received_requests) == request_count


def test_audited_weekly_message_writer_with_text_off_gives_both_templates() -> None:
    """AI text switched off: both languages are the template text."""
    facts = build_design_weekly_message_facts()
    written = build_weekly_message_writer(FixedClock(MOMENT)).write(MERCHANT_ID, facts)
    assert (written.english_source, written.tamil_source) == (
        AiTextSource.TEMPLATE,
        AiTextSource.TEMPLATE,
    )
    assert written.messages.english == render_weekly_template(MessageLanguage.ENGLISH, facts)


def test_audited_weekly_message_writer_unexpected_flow_error_gives_both_templates(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A RuntimeError in the flow gives the template in both languages and a FLOW_FAILED line."""
    port = ScriptedExplanationTextPort({CustomerLanguage.ENGLISH: WEEKLY_ENGLISH_AI_TEXT})
    writer = AuditedWeeklyMessageWriter(
        build_weekly_message_flow(port, FailingFlowRunner(RuntimeError("secret text"))),
        WeeklyMessageTemplate(format_paise_as_whole_rupees),
        build_weekly_message_cache(FixedClock(MOMENT)),
        AiUsageLogger(TEST_AI_PRICE_LIST),
    )
    facts = build_design_weekly_message_facts()
    with caplog.at_level(logging.INFO):
        written = writer.write(MERCHANT_ID, facts)
    assert (written.english_source, written.tamil_source) == (
        AiTextSource.TEMPLATE,
        AiTextSource.TEMPLATE,
    )
    assert written.messages.tamil == render_weekly_template(MessageLanguage.TAMIL, facts)
    assert read_usage_outcomes(caplog) == ["FLOW_FAILED"]
    assert "secret text" not in caplog.text
