"""OpenAPI examples and documented errors of the M4 hand-off endpoints."""

from emi_copilot.api.controllers.sale_documentation import (
    CHOOSING_SALE_SUMMARY_EXAMPLE,
    NO_COST_CHOSEN_PLAN_EXAMPLE,
)
from emi_copilot.api.openapi_documentation import ProblemExample

EXAMPLE_ORDER_ID = "01JD5Z0Q8M6X3V2N7B4C9K1T0A"
EXAMPLE_PAYMENT_URL = "https://mock-payments.invalid/pay/mock-link-0123456789abcdef0123"
SALE_HANDOFF_EXAMPLE = {
    "paymentStatus": "WAITING",
    "paymentConfirmedAt": None,
    "sale": {
        **CHOOSING_SALE_SUMMARY_EXAMPLE,
        "status": "READY_TO_PAY",
        "statusChangedAt": "2026-11-15T09:36:00Z",
        "chosenPlan": NO_COST_CHOSEN_PLAN_EXAMPLE,
    },
    "edcInstructions": {
        "emiProgramme": "BRAND_EMI",
        "productName": "Example phone, 128 GB",
        "tenureInMonths": 6,
        "isNoExtraCost": True,
        "amountInPaise": 2_200_000,
    },
    "latestPaymentLink": {
        "orderId": EXAMPLE_ORDER_ID,
        "paymentUrl": EXAMPLE_PAYMENT_URL,
        "status": "AWAITING_PAYMENT",
    },
}
SALE_PAYMENT_LINK_EXAMPLE = {
    "orderId": EXAMPLE_ORDER_ID,
    "paymentUrl": EXAMPLE_PAYMENT_URL,
    "amountInPaise": 2_200_000,
    "status": "AWAITING_PAYMENT",
}
PAID_SALE_PAYMENT_STATUS_EXAMPLE = {
    "paymentStatus": "PAID",
    "paymentConfirmedAt": "2026-11-15T09:41:00Z",
}
SALE_HAS_NO_AGREED_PLAN_PROBLEM = ProblemExample(
    409,
    "SALE_STATE_CONFLICT",
    "Not possible in the sale's current status",
    "A sale that is CHOOSING has no agreed plan to hand off.",
    "The customer has not agreed to a plan yet (CHOOSING), or the sale EXPIRED.",
)
SALE_TAKES_NO_NEW_LINK_PROBLEM = ProblemExample(
    409,
    "SALE_STATE_CONFLICT",
    "Not possible in the sale's current status",
    "A sale that is PAID takes no new payment link.",
    "The sale is CHOOSING, EXPIRED or already PAID, and the key is new.",
)
CHOSEN_PLAN_NO_LONGER_OFFERED_PROBLEM = ProblemExample(
    409,
    "CHOSEN_PLAN_NO_LONGER_OFFERED",
    "Agreed plan no longer offered",
    "The gateway no longer quotes the agreed plan with the figures that were shown.",
    "The fresh quote differs from the agreed plan in any figure, or the plan is gone; the "
    "customer has to choose again.",
)
