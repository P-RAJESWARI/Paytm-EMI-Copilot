"""WeeklyMessageService: reads one week's message and marks it sent once (plan Q14)."""

from dataclasses import dataclass
from datetime import date, datetime

from emi_copilot.adapters.weekly_message_delivery.port import WeeklyMessageDeliveryPort
from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.domain.reports.reporting_period import ReportingPeriod
from emi_copilot.domain.reports.weekly_message_record import WeeklyMessageDelivery
from emi_copilot.domain.reports.weekly_message_template import WeeklyMessageFacts, WeeklyMessages
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.ai.ai_flow_types import AiTextSource
from emi_copilot.services.report_periods import ReportPeriods
from emi_copilot.services.report_services import (
    FunnelReportService,
    MissedSalesReportService,
    MoneyDueReportService,
    SuggestedActionsService,
)
from emi_copilot.services.weekly_message_writer import WeeklyMessageWriter, WrittenWeeklyMessages


@dataclass(frozen=True, slots=True)
class WeeklyMessageView:
    """One week's message in both languages, who wrote each, and when it was sent (or None)."""

    period: ReportingPeriod
    messages: WeeklyMessages
    english_source: AiTextSource
    tamil_source: AiTextSource
    sent_at: datetime | None

    @classmethod
    def of(
        cls, period: ReportingPeriod, written: WrittenWeeklyMessages, sent_at: datetime | None
    ) -> "WeeklyMessageView":
        """Builds the view of a written message."""
        return cls(period, written.messages, written.english_source, written.tamil_source, sent_at)


@dataclass(frozen=True, slots=True)
class WeeklyMessageReports:
    """The report services one week's message is written from."""

    funnel: FunnelReportService
    missed_sales: MissedSalesReportService
    suggested_actions: SuggestedActionsService
    money_due: MoneyDueReportService


class WeeklyMessageService:
    """Writes the week's message from the report numbers and records "sent" exactly once.

    The writer (audited AI text, or the template per language) keeps the shown text for a
    while, so a repeat read and "send" use exactly the text that was shown; it is never stored.
    Sending records the moment under the (shop, week) unique key; only the request that
    records it hands the message to the delivery port, after the commit, so a repeat send
    changes nothing and sends nothing.
    """

    def __init__(  # noqa: PLR0913 - one parameter per collaborator
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        id_generator: IdGenerator,
        report_periods: ReportPeriods,
        reports: WeeklyMessageReports,
        writer: WeeklyMessageWriter,
        delivery: WeeklyMessageDeliveryPort,
    ) -> None:
        """Keeps the collaborators."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._id_generator = id_generator
        self._report_periods = report_periods
        self._reports = reports
        self._writer = writer
        self._delivery = delivery

    def get_weekly_message(
        self, principal: MerchantPrincipal, period_start_date: date | None
    ) -> WeeklyMessageView:
        """Gives the week's message (the current week when no Monday is given)."""
        period = self._report_periods.week_starting(period_start_date)
        written = self._write_messages(principal, period)
        with self._unit_of_work_factory() as unit_of_work:
            sent_at = unit_of_work.weekly_messages.find_sent_at(
                principal.merchant_id, period.period_start_date
            )
        return WeeklyMessageView.of(period, written, sent_at)

    def send_weekly_message(
        self, principal: MerchantPrincipal, period_start_date: date
    ) -> WeeklyMessageView:
        """Marks the week's message sent once and delivers it then; a repeat is a no-op."""
        period = self._report_periods.week_starting(period_start_date)
        written = self._write_messages(principal, period)
        delivery = WeeklyMessageDelivery(
            merchant_id=principal.merchant_id,
            period_start_date=period.period_start_date,
            messages=written.messages,
        )
        with self._unit_of_work_factory() as unit_of_work:
            record = unit_of_work.weekly_messages.record_sent_once(
                self._id_generator.new_id(),
                principal.merchant_id,
                period.period_start_date,
                self._clock.now(),
            )
            if record.was_sent_now:
                unit_of_work.call_after_commit(
                    lambda: self._delivery.deliver_weekly_message(delivery)
                )
        return WeeklyMessageView.of(period, written, record.sent_at)

    def _write_messages(
        self, principal: MerchantPrincipal, period: ReportingPeriod
    ) -> WrittenWeeklyMessages:
        """Builds every report the message names, for the week, and writes both languages."""
        return self._writer.write(
            principal.merchant_id,
            WeeklyMessageFacts(
                period=period,
                funnel=self._reports.funnel.build_report(principal, period),
                missed_sales=self._reports.missed_sales.build_report(principal, period),
                money_due=self._reports.money_due.get_money_due(principal),
                suggested_actions=self._reports.suggested_actions.build_actions(principal, period),
            ),
        )
