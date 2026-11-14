"""WeeklyMessageTemplate: the shop's weekly message, written from the report numbers (plan Q14).

The backend renders this text because it is a sent artifact, like Layer 4's AI text; the money
formatter is injected (core/indian_rupee_formatter.py), so the domain imports no other layer. A
sentence whose number is suppressed (1 to 4 customers) or missing is left out, never guessed.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.reports.funnel_report import FunnelReport
from emi_copilot.domain.reports.missed_sales import MissedSalesReport
from emi_copilot.domain.reports.money_due_report import MoneyDueReport
from emi_copilot.domain.reports.reporting_period import ReportingPeriod
from emi_copilot.domain.reports.suggested_actions import (
    CheaperModelAction,
    LongerNoCostPlanAction,
    SuggestedAction,
)
from emi_copilot.domain.reports.weekly_message_wording import (
    WORDING_BY_LANGUAGE,
    MessageLanguage,
    WeeklyMessageWording,
)

RupeeFormatter = Callable[[int], str]
"""Turns integer paise into the text shown for it, for example 366667 into "₹3,667"."""


@dataclass(frozen=True, slots=True)
class WeeklyMessageFacts:
    """Every report figure one week's message may mention, already suppressed where needed."""

    period: ReportingPeriod
    funnel: FunnelReport
    missed_sales: MissedSalesReport
    money_due: MoneyDueReport
    suggested_actions: tuple[SuggestedAction, ...]


@dataclass(frozen=True, slots=True)
class WeeklyMessageText:
    """One language's message: a title and its paragraphs (M8's p1 to p3, empty ones left out)."""

    title: str
    paragraphs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WeeklyMessages:
    """The same week's message in English and in Tamil."""

    english: WeeklyMessageText
    tamil: WeeklyMessageText


def _join_sentences(sentences: Sequence[str | None]) -> str:
    """Joins the sentences that exist into one paragraph."""
    return " ".join(sentence for sentence in sentences if sentence)


class WeeklyMessageTemplate:
    """Writes the weekly message in both languages from one set of facts.

    The same facts always give the same text, and every number in it is a report number.
    """

    def __init__(self, format_paise_as_rupees: RupeeFormatter) -> None:
        """Keeps the formatter every amount in the text goes through."""
        self._format_paise_as_rupees = format_paise_as_rupees

    def render(self, facts: WeeklyMessageFacts) -> WeeklyMessages:
        """Writes the message in English and in Tamil."""
        return WeeklyMessages(
            english=self.render_in(MessageLanguage.ENGLISH, facts),
            tamil=self.render_in(MessageLanguage.TAMIL, facts),
        )

    def render_in(self, language: MessageLanguage, facts: WeeklyMessageFacts) -> WeeklyMessageText:
        """Writes the title and the three paragraphs: sales, missed and due, the one action."""
        wording = WORDING_BY_LANGUAGE[language]
        paragraphs = (
            _join_sentences(self._describe_sales(wording, facts.funnel)),
            _join_sentences(
                [
                    self._describe_missed_sales(wording, facts.missed_sales),
                    self._describe_money_due(wording, facts.money_due),
                ]
            ),
            _join_sentences([self._describe_first_action(wording, facts.suggested_actions)]),
        )
        return WeeklyMessageText(
            title=_describe_period(wording, facts.period),
            paragraphs=tuple(paragraph for paragraph in paragraphs if paragraph),
        )

    def _format(self, amount: Money) -> str:
        """Formats one amount for the text."""
        return self._format_paise_as_rupees(amount.to_paise())

    def _describe_sales(self, wording: WeeklyMessageWording, funnel: FunnelReport) -> list[str]:
        """Says how many started customers paid, and after which stage most were lost."""
        started = funnel.count_for(FunnelStage.STARTED).customer_count
        paid = funnel.count_for(FunnelStage.PAID).customer_count
        if started == 0:
            return [wording.no_sales_yet]
        sentences = []
        if started is not None and paid is not None:
            sentences.append(wording.bought_on_emi.format(paid_count=paid, started_count=started))
        drop = funnel.biggest_drop
        if drop is not None and not drop.count.is_suppressed:
            sentences.append(wording.biggest_drop_after_stage[drop.after_stage])
        return sentences

    def _describe_missed_sales(
        self, wording: WeeklyMessageWording, missed_sales: MissedSalesReport
    ) -> str | None:
        """Says how many wanted less than the ceiling with nothing extra; None when not shown."""
        missed_count = missed_sales.missed_count.customer_count
        if not missed_count or missed_sales.budget_ceiling is None:
            return None
        return wording.missed_sales.format(
            missed_count=missed_count, budget_ceiling=self._format(missed_sales.budget_ceiling)
        )

    def _describe_money_due(
        self, wording: WeeklyMessageWording, money_due: MoneyDueReport
    ) -> str | None:
        """Says what brands owe and when the first payment is expected; None when nothing is."""
        if money_due.next_expected_date is None:
            return None
        return wording.money_due.format(
            total_due=self._format(money_due.total_due),
            next_date=_describe_day(money_due.next_expected_date, wording.due_date_month_names),
        )

    def _describe_first_action(
        self, wording: WeeklyMessageWording, suggested_actions: Sequence[SuggestedAction]
    ) -> str | None:
        """Says the first suggested action with its computed figures; None without one."""
        if not suggested_actions:
            return None
        action = suggested_actions[0]
        if isinstance(action, LongerNoCostPlanAction):
            return self._describe_longer_no_cost_action(wording, action)
        return self._describe_cheaper_model_action(wording, action)

    def _describe_longer_no_cost_action(
        self, wording: WeeklyMessageWording, action: LongerNoCostPlanAction
    ) -> str:
        """Names the tenures to ask the brand for and the monthly figure of each."""
        joiner = wording.alternatives_joiner
        return wording.longer_no_cost_action.format(
            tenures=joiner.join(
                str(tenure.tenure_in_months) for tenure in action.suggested_tenures
            ),
            product_name=action.product_name,
            monthly_amounts=joiner.join(
                self._format(tenure.monthly_installment) for tenure in action.suggested_tenures
            ),
        )

    def _describe_cheaper_model_action(
        self, wording: WeeklyMessageWording, action: CheaperModelAction
    ) -> str:
        """Names the cheaper model, its price and its no-extra-cost monthly figure."""
        return wording.cheaper_model_action.format(
            product_name=action.product_name,
            list_price=self._format(action.list_price),
            monthly_amount=self._format(action.monthly_installment),
            tenure=action.tenure_in_months,
        )


def _describe_day(day: date, month_names: Sequence[str]) -> str:
    """Gives "13 Jan" style text: the day number and the month's name."""
    return f"{day.day} {month_names[day.month - 1]}"


def _describe_period(wording: WeeklyMessageWording, period: ReportingPeriod) -> str:
    """Gives the title with the period's first and last dates, the month named once if shared."""
    first_date, last_date = period.period_start_date, period.period_end_date
    month_names = wording.title_month_names
    if first_date.month == last_date.month:
        return wording.title_within_one_month.format(
            first_day=first_date.day,
            last_day=last_date.day,
            last_month=month_names[last_date.month - 1],
        )
    return wording.title_across_two_months.format(
        first_day=first_date.day,
        first_month=month_names[first_date.month - 1],
        last_day=last_date.day,
        last_month=month_names[last_date.month - 1],
    )
