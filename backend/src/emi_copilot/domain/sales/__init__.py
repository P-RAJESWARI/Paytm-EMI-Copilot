"""Sale types: the sale, its status and state machine, the chosen plan and the session code."""

from emi_copilot.domain.sales.chosen_plan import ChosenPlan, ChosenPlanDictionary
from emi_copilot.domain.sales.counter_day import CounterDay
from emi_copilot.domain.sales.sale import CustomerQrTokenState, Sale, SaleIdempotency
from emi_copilot.domain.sales.sale_state_machine import (
    PaymentOutcomeEffect,
    SaleCommand,
    SalePaymentOutcome,
    SaleStateMachine,
)
from emi_copilot.domain.sales.sale_status import (
    OPEN_SALE_STATUSES,
    STATUSES_WITH_CHOSEN_PLAN,
    SaleStatus,
)
from emi_copilot.domain.sales.session_code import SESSION_CODE_DIGIT_COUNT, SessionCode

__all__ = [
    "OPEN_SALE_STATUSES",
    "SESSION_CODE_DIGIT_COUNT",
    "STATUSES_WITH_CHOSEN_PLAN",
    "ChosenPlan",
    "ChosenPlanDictionary",
    "CounterDay",
    "CustomerQrTokenState",
    "PaymentOutcomeEffect",
    "Sale",
    "SaleCommand",
    "SaleIdempotency",
    "SalePaymentOutcome",
    "SaleStateMachine",
    "SaleStatus",
    "SessionCode",
]
