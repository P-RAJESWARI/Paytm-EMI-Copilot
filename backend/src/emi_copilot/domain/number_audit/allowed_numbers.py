"""AllowedNumbers: the whole rupee amounts and plain numbers an AI text may mention."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from emi_copilot.domain.money import Money
from emi_copilot.domain.number_audit.number_token_extractor import NumberTokenExtractor
from emi_copilot.domain.reports.money_due_report import MoneyDueReport
from emi_copilot.domain.reports.small_count_suppression import ReportedCount
from emi_copilot.domain.reports.suggested_actions import LongerNoCostPlanAction, SuggestedAction
from emi_copilot.domain.reports.weekly_message_template import WeeklyMessageFacts
from emi_copilot.domain.sales import ChosenPlan

_PAISE_PER_RUPEE = 100


def whole_rupees_of(amount: Money) -> int:
    """Gives the whole rupees shown for an amount: paise rounded half-up, as the screens show."""
    whole_rupees = (Decimal(amount.to_paise()) / _PAISE_PER_RUPEE).quantize(
        Decimal(1), rounding=ROUND_HALF_UP
    )
    return int(whole_rupees)


def numbers_written_in(label_texts: Iterable[str]) -> frozenset[int]:
    """Gives the value of every checkable number inside labels such as "128 GB" or "A15 5G"."""
    extractor = NumberTokenExtractor()
    return frozenset(
        token.value
        for label_text in label_texts
        for token in extractor.extract(label_text)
        if token.value is not None
    )


def shown_counts(reported_counts: Iterable[ReportedCount | None]) -> frozenset[int]:
    """Gives the counts the merchant may see; suppressed counts (1 to 4) are never allowed."""
    return frozenset(
        reported_count.customer_count
        for reported_count in reported_counts
        if reported_count is not None and reported_count.customer_count is not None
    )


def day_and_year_numbers(dates: Iterable[date]) -> frozenset[int]:
    """Gives the day of the month and the year of each date, as "13 Jan 2027" writes them."""
    return frozenset(number for day in dates for number in (day.day, day.year))


def action_amounts(action: SuggestedAction) -> tuple[Money, ...]:
    """Gives every money figure of one suggested action."""
    if isinstance(action, LongerNoCostPlanAction):
        ceiling = () if action.budget_ceiling is None else (action.budget_ceiling,)
        return (
            action.current_no_cost_monthly,
            *ceiling,
            *(tenure.monthly_installment for tenure in action.suggested_tenures),
        )
    return (action.list_price, action.monthly_installment)


def action_tenures(action: SuggestedAction) -> tuple[int, ...]:
    """Gives every tenure in months of one suggested action."""
    if isinstance(action, LongerNoCostPlanAction):
        return (
            action.current_no_cost_tenure_in_months,
            *(tenure.tenure_in_months for tenure in action.suggested_tenures),
        )
    return (action.tenure_in_months,)


def weekly_money_due_amounts(money_due: MoneyDueReport) -> tuple[Money, ...]:
    """Gives the total due from brands and each batch amount."""
    return (money_due.total_due, *(batch.amount for batch in money_due.batches))


def weekly_dates(facts: WeeklyMessageFacts) -> tuple[date, ...]:
    """Gives the week's first and last dates, each batch date and the next expected payment."""
    next_expected_date = facts.money_due.next_expected_date
    return (
        facts.period.period_start_date,
        facts.period.period_end_date,
        *(batch.expected_date for batch in facts.money_due.batches),
        *(() if next_expected_date is None else (next_expected_date,)),
    )


def weekly_counts(facts: WeeklyMessageFacts) -> tuple[ReportedCount | None, ...]:
    """Gives every reported count of the week: funnel stages, missed sales and biggest drop."""
    drop = facts.funnel.biggest_drop
    return (
        *(stage.count for stage in facts.funnel.stages),
        facts.missed_sales.missed_count,
        None if drop is None else drop.count,
    )


# Pattern: Value Object. The fixed set of figures an AI text is checked against, built only from
# engine and report output, so the audit itself never computes or guesses a number.
@dataclass(frozen=True, slots=True)
class AllowedNumbers:
    """Whole rupee amounts a ₹ figure may take, and plain numbers any other figure may take."""

    rupee_amounts: frozenset[int]
    plain_numbers: frozenset[int]

    @classmethod
    def for_plan_explanation(
        cls, plan: ChosenPlan, label_texts: tuple[str, ...]
    ) -> "AllowedNumbers":
        """Allows the plan's monthly, extra, total and price, its tenure and label digits."""
        amounts = (plan.monthly_installment, plan.extra_in_total, plan.total_payable, plan.price)
        return cls(
            rupee_amounts=frozenset(whole_rupees_of(amount) for amount in amounts),
            plain_numbers=frozenset({plan.tenure_in_months}) | numbers_written_in(label_texts),
        )

    @classmethod
    def for_weekly_message(cls, facts: WeeklyMessageFacts) -> "AllowedNumbers":
        """Allows the figures WeeklyMessageTemplate may say, plus the brand batches.

        Mirrors the template: the missed sales ceiling and every action are left out while the
        missed count is suppressed, because they would describe one to four customers.
        """
        is_missed_count_shown = not facts.missed_sales.missed_count.is_suppressed
        actions = facts.suggested_actions if is_missed_count_shown else ()
        ceiling = facts.missed_sales.budget_ceiling if is_missed_count_shown else None
        amounts = [
            *weekly_money_due_amounts(facts.money_due),
            *(amount for action in actions for amount in action_amounts(action)),
            *(() if ceiling is None else (ceiling,)),
        ]
        return cls(
            rupee_amounts=frozenset(whole_rupees_of(amount) for amount in amounts),
            plain_numbers=shown_counts(weekly_counts(facts))
            | day_and_year_numbers(weekly_dates(facts))
            | frozenset(tenure for action in actions for tenure in action_tenures(action))
            | numbers_written_in(action.product_name for action in actions),
        )
