"""Suggested actions for M5's "What you can do to sell more": reason codes and paise, no prose.

The words are the frontend's (and the weekly message template's); each strategy decides only
whether its action applies and with which figures. Every figure is a gateway quote or comes
from the existing NoCostStrategy; nothing new is calculated here.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from emi_copilot.domain.emi import NoCostStrategy
from emi_copilot.domain.errors import EmiScheduleNotRepresentableError
from emi_copilot.domain.money import Money
from emi_copilot.domain.reports.missed_sales import MissedSalesAnalysis
from emi_copilot.domain.reports.small_count_suppression import (
    ReportedCount,
    SmallCountSuppressionPolicy,
)

LONGER_NO_COST_TENURES_IN_MONTHS = (9, 12)
"""The longer no-cost tenures to ask a brand for (M5's "9 or 12 months")."""


class SuggestedActionCode(StrEnum):
    """Which action is suggested; the frontend maps each code to translated text."""

    ASK_BRAND_FOR_LONGER_NO_COST_PLAN = "ASK_BRAND_FOR_LONGER_NO_COST_PLAN"
    KEEP_CHEAPER_MODEL_READY = "KEEP_CHEAPER_MODEL_READY"


@dataclass(frozen=True, slots=True)
class SuggestedNoCostTenure:
    """A longer no-cost tenure and its regular monthly installment on the list price."""

    tenure_in_months: int
    monthly_installment: Money


@dataclass(frozen=True, slots=True)
class LongerNoCostPlanAction:
    """Ask the brand for a longer no-cost plan on the product most missed sales were for."""

    product_id: str
    product_name: str
    current_no_cost_tenure_in_months: int
    current_no_cost_monthly: Money
    suggested_tenures: tuple[SuggestedNoCostTenure, ...]
    missed_count: ReportedCount
    budget_ceiling: Money | None

    @property
    def action_code(self) -> SuggestedActionCode:
        """Gives this action's stable code."""
        return SuggestedActionCode.ASK_BRAND_FOR_LONGER_NO_COST_PLAN


@dataclass(frozen=True, slots=True)
class CheaperModelAction:
    """Keep a cheaper model ready: its no-cost plan fits the budgets that were missed."""

    product_id: str
    product_name: str
    list_price: Money
    monthly_installment: Money
    tenure_in_months: int

    @property
    def action_code(self) -> SuggestedActionCode:
        """Gives this action's stable code."""
        return SuggestedActionCode.KEEP_CHEAPER_MODEL_READY


SuggestedAction = LongerNoCostPlanAction | CheaperModelAction


@dataclass(frozen=True, slots=True)
class SuggestionContext:
    """What every strategy may read: the period's missed-sales analysis and the count policy."""

    analysis: MissedSalesAnalysis
    policy: SmallCountSuppressionPolicy


# Pattern: Strategy. Each suggestion rule is independent and tested on its own.
class SuggestedActionStrategy(ABC):
    """Decides whether one kind of action applies, and gives it with its figures."""

    @abstractmethod
    def suggest(self, context: SuggestionContext) -> tuple[SuggestedAction, ...]:
        """Gives this strategy's actions for the context; empty when it does not apply."""


class LongerNoCostPlanSuggestion(SuggestedActionStrategy):
    """Fires when the insight product has missed sales: longer no-cost tenures on its price."""

    def suggest(self, context: SuggestionContext) -> tuple[SuggestedAction, ...]:
        """Gives one action with the 9 and 12-month installments, or none without an insight."""
        insight = context.analysis.insight
        if insight is None:
            return ()
        lowest_offer = insight.product_offers.lowest_no_extra_cost_offer
        if lowest_offer is None:
            return ()
        product = insight.product_offers.product
        suggested_tenures = tuple(
            tenure
            for tenure in (
                _find_no_cost_tenure(product.list_price, tenure_in_months)
                for tenure_in_months in LONGER_NO_COST_TENURES_IN_MONTHS
                if tenure_in_months > lowest_offer.offer.tenure_in_months
            )
            if tenure is not None
        )
        if not suggested_tenures:
            return ()
        return (
            LongerNoCostPlanAction(
                product_id=product.id,
                product_name=product.name,
                current_no_cost_tenure_in_months=lowest_offer.offer.tenure_in_months,
                current_no_cost_monthly=lowest_offer.quoted_monthly_installment,
                suggested_tenures=suggested_tenures,
                missed_count=context.policy.report(insight.missed_count),
                budget_ceiling=insight.budget_ceiling,
            ),
        )


def _find_no_cost_tenure(list_price: Money, tenure_in_months: int) -> SuggestedNoCostTenure | None:
    """Gives the no-cost regular installment over the tenure, or None if it cannot be split."""
    try:
        schedule = NoCostStrategy().calculate_schedule(list_price, tenure_in_months)
    except EmiScheduleNotRepresentableError:
        return None
    return SuggestedNoCostTenure(tenure_in_months, schedule.regular_installment)


class CheaperModelSuggestion(SuggestedActionStrategy):
    """Fires when a cheaper product's no-extra-cost monthly fits under the missed ceiling.

    Only the dearest such product is suggested (ties: name), the model closest to what the
    customers came for.
    """

    def suggest(self, context: SuggestionContext) -> tuple[SuggestedAction, ...]:
        """Gives one action for the closest cheaper model that fits, or none."""
        insight = context.analysis.insight
        if insight is None or insight.budget_ceiling is None:
            return ()
        insight_product = insight.product_offers.product
        fitting_models = [
            (candidate.product_offers.product, lowest_offer)
            for candidate in context.analysis.products_missed_sales
            for lowest_offer in (candidate.product_offers.lowest_no_extra_cost_offer,)
            if lowest_offer is not None
            and lowest_offer.quoted_monthly_installment <= insight.budget_ceiling
            and candidate.product_offers.product.id != insight_product.id
            and candidate.product_offers.product.list_price < insight_product.list_price
        ]
        if not fitting_models:
            return ()
        product, lowest_offer = min(
            fitting_models,
            key=lambda fitting_model: (
                -fitting_model[0].list_price.to_paise(),
                fitting_model[0].name,
            ),
        )
        return (
            CheaperModelAction(
                product_id=product.id,
                product_name=product.name,
                list_price=product.list_price,
                monthly_installment=lowest_offer.quoted_monthly_installment,
                tenure_in_months=lowest_offer.offer.tenure_in_months,
            ),
        )


SUGGESTED_ACTION_STRATEGIES: tuple[SuggestedActionStrategy, ...] = (
    LongerNoCostPlanSuggestion(),
    CheaperModelSuggestion(),
)
"""Every strategy, in the stable order their actions are listed."""


def suggest_actions(
    context: SuggestionContext,
    strategies: Sequence[SuggestedActionStrategy] = SUGGESTED_ACTION_STRATEGIES,
) -> tuple[SuggestedAction, ...]:
    """Gives every strategy's actions, strategy by strategy, in a stable order."""
    return tuple(action for strategy in strategies for action in strategy.suggest(context))
