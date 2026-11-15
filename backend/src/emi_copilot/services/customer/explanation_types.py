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
    """Who wrote the explanation; Layer 4 adds the audited AI source beside the template."""

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


class PlanExplainer(Protocol):
    """Anything that explains one plan in plain words; Layer 4 wraps the template with AI."""

    def explain(self, plan: ChosenPlan, language: CustomerLanguage) -> ExplanationText:
        """Gives the explanation of the plan's figures in the language."""
        ...
