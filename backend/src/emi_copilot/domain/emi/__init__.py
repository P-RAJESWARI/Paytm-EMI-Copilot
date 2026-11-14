"""EMI calculation strategies and the schedule value object they produce."""

from emi_copilot.domain.emi.emi_calculation_strategy import EmiCalculationStrategy
from emi_copilot.domain.emi.emi_schedule import (
    EmiSchedule,
    require_valid_emi_terms,
    split_total_payable_evenly,
)
from emi_copilot.domain.emi.no_cost_strategy import NoCostStrategy
from emi_copilot.domain.emi.quoted_total_strategy import QuotedTotalStrategy
from emi_copilot.domain.emi.reducing_balance_strategy import ReducingBalanceStrategy

__all__ = [
    "EmiCalculationStrategy",
    "EmiSchedule",
    "NoCostStrategy",
    "QuotedTotalStrategy",
    "ReducingBalanceStrategy",
    "require_valid_emi_terms",
    "split_total_payable_evenly",
]
