"""Documented problem answers and the STUB note shared by the customer flow operations."""

from emi_copilot.api.openapi_documentation import (
    GATEWAY_TIMEOUT_PROBLEM,
    REQUEST_VALIDATION_PROBLEM,
    ProblemExample,
)

STUB_OPERATION_NOTE = (
    "STUB (DESIGN_SPEC §4 sample data) until Phase 3C; not mounted in the main app (ADR 0012). "
    "Money is integer paise, shares are integer basis points, errors are "
    "application/problem+json. "
)
SESSION_TOKEN_NOTE = "Needs the X-Customer-Session-Token header. "  # noqa: S105 - prose

CUSTOMER_QR_TOKEN_INVALID_PROBLEM = ProblemExample(
    401,
    "CUSTOMER_QR_TOKEN_INVALID",
    "QR code not valid",
    "This QR code is not valid; ask the shop for a new QR.",
    "The QR token is unknown or no longer valid; the shop can show a new QR.",
)
CUSTOMER_SESSION_TOKEN_INVALID_PROBLEM = ProblemExample(
    401,
    "CUSTOMER_SESSION_TOKEN_INVALID",
    "Customer session not valid",
    "This session link is not valid; ask the shop for a new QR.",
    "The session token is missing, opens no session, or the session has ended.",
)
CUSTOMER_SESSION_NOT_FOUND_PROBLEM = ProblemExample(
    404,
    "CUSTOMER_SESSION_NOT_FOUND",
    "Customer session not found",
    "No customer session has this id.",
    "The token is valid but belongs to another session id, whether that id exists or not.",
)
BUDGET_NOT_CONFIRMED_PROBLEM = ProblemExample(
    409,
    "BUDGET_NOT_CONFIRMED",
    "Monthly budget not confirmed",
    "Confirm a monthly budget before this step.",
    "The monthly budget has not been confirmed yet.",
)
CONSENT_ALREADY_GIVEN_PROBLEM = ProblemExample(
    409,
    "CONSENT_ALREADY_GIVEN",
    "Consent already given",
    "Consent was already given in this session.",
    "Consent was already recorded in this session under another Idempotency-Key.",
)
CONSENT_NOT_GIVEN_PROBLEM = ProblemExample(
    409,
    "CONSENT_NOT_GIVEN",
    "Consent not given yet",
    "There is no receipt until the plan is agreed.",
    "The plan has not been agreed to yet.",
)
OTP_NOT_REQUESTED_PROBLEM = ProblemExample(
    422,
    "OTP_NOT_REQUESTED",
    "One-time code not requested",
    "Request a one-time code before agreeing.",
    "No one-time code was requested for this session.",
)
OTP_INCORRECT_PROBLEM = ProblemExample(
    422,
    "OTP_INCORRECT",
    "One-time code does not match",
    "This code does not match; check it or request a new code.",
    "The code does not match; the customer may try again or request a new code.",
)
OTP_EXPIRED_PROBLEM = ProblemExample(
    422,
    "OTP_EXPIRED",
    "One-time code expired",
    "This code has expired; request a new code.",
    "The code is past its 5-minute lifetime; request a new one.",
)
OFFER_NOT_QUOTED_PROBLEM = ProblemExample(
    404,
    "OFFER_NOT_FOUND",
    "Offer not found",
    "The chosen offer is not quoted for this item and price.",
    "The chosen offer is not quoted for the session's item.",
)
IDEMPOTENCY_KEY_REUSED_PROBLEM = ProblemExample(
    422,
    "IDEMPOTENCY_KEY_REUSED",
    "Idempotency key reused",
    "The Idempotency-Key was already used with a different body.",
    "The Idempotency-Key was already used with a different body.",
)
CUSTOMER_GATEWAY_UNAVAILABLE_PROBLEM = ProblemExample(
    502,
    "PAYMENT_GATEWAY_UNAVAILABLE",
    "Payment gateway unavailable",
    "The gateway could not serve the call.",
    "The payment gateway could not quote plans right now.",
)

INVALID_PLAN_SELECTION_PROBLEM = ProblemExample(
    422,
    "INVALID_PLAN_SELECTION",
    "Plan selection not offered",
    "This down payment is not offered for this plan.",
    "The product or the down payment is not one this session offers.",
)
SHOWN_PLAN_CHANGED_PROBLEM = ProblemExample(
    409,
    "SHOWN_PLAN_CHANGED",
    "Plan figures changed",
    "The plan figures changed; show the plans again.",
    "A fresh quote no longer matches the monthly or total shown; nothing was recorded.",
)

PLAN_SELECTION_PROBLEMS = (INVALID_PLAN_SELECTION_PROBLEM, SHOWN_PLAN_CHANGED_PROBLEM)
SESSION_PROBLEMS = (
    CUSTOMER_SESSION_TOKEN_INVALID_PROBLEM,
    CUSTOMER_SESSION_NOT_FOUND_PROBLEM,
    REQUEST_VALIDATION_PROBLEM,
)
QUOTING_PROBLEMS = (CUSTOMER_GATEWAY_UNAVAILABLE_PROBLEM, GATEWAY_TIMEOUT_PROBLEM)
