"""What the C7 explanation is made of, and the interface every explainer implements."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.money import Money
from emi_copilot.domain.sales import ChosenPlan

RupeeFormatter = Callable[[int], str]
"""Turns integer paise into the whole-rupee text shown for it, for example 366667 into "₹3,667"."""


class ExplanationSource(StrEnum):
    """Who wrote the explanation: AI text that passed the number audit, or the standard text."""

    AI_AUDITED = "AI_AUDITED"
    TEMPLATE = "TEMPLATE"


class HighlightedAmountKind(StrEnum):
    """Which plan figure a highlighted amount is (C7 shows two beside the text)."""

    MONTHLY_INSTALLMENT = "MONTHLY_INSTALLMENT"
    EXTRA_IN_TOTAL = "EXTRA_IN_TOTAL"


@dataclass(frozen=True, slots=True)
class HighlightedAmount:
    """One figure the text mentions, exactly as the engine computed it."""

    kind: HighlightedAmountKind
    amount: Money


@dataclass(frozen=True, slots=True)
class ExplanationText:
    """Plain words about one plan; every rupee amount in the text is one of the highlights."""

    text: str
    language: CustomerLanguage
    source: ExplanationSource
    highlighted_amounts: tuple[HighlightedAmount, ...]


def highlight_plan_figures(plan: ChosenPlan) -> tuple[HighlightedAmount, ...]:
    """Gives the monthly and the extra in total exactly as the engine computed them."""
    return (
        HighlightedAmount(HighlightedAmountKind.MONTHLY_INSTALLMENT, plan.monthly_installment),
        HighlightedAmount(HighlightedAmountKind.EXTRA_IN_TOTAL, plan.extra_in_total),
    )


class PlanExplainer(Protocol):
    """Anything that explains one plan in plain words; Layer 4 wraps the template with AI."""

    def explain(
        self,
        plan: ChosenPlan,
        language: CustomerLanguage,
        *,
        customer_session_id: str | None = None,
    ) -> ExplanationText:
        """Gives the explanation of the plan's figures; the session id only labels usage logs."""
        ...
