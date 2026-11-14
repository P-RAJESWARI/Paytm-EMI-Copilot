"""Smarter alternatives (C6): down payment, longer tenure and cheaper model, engine-recomputed."""

from emi_copilot.domain.alternatives.alternative_kind import AlternativeKind
from emi_copilot.domain.alternatives.cheaper_model_quote import CheaperModelQuote
from emi_copilot.domain.alternatives.down_payment_rule import (
    DEFAULT_DOWN_PAYMENT_ROUNDING_STEP,
    DownPaymentRule,
)
from emi_copilot.domain.alternatives.plan_alternative import PlanAlternative, PlanAlternatives
from emi_copilot.domain.alternatives.plan_alternative_finder import PlanAlternativeFinder

__all__ = [
    "DEFAULT_DOWN_PAYMENT_ROUNDING_STEP",
    "AlternativeKind",
    "CheaperModelQuote",
    "DownPaymentRule",
    "PlanAlternative",
    "PlanAlternativeFinder",
    "PlanAlternatives",
]
