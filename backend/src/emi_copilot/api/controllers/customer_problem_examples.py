"""Documented problem answers and the notes shared by the customer flow operations."""

from typing import Any

from emi_copilot.api.openapi_documentation import (
    GATEWAY_TIMEOUT_PROBLEM,
    REQUEST_VALIDATION_PROBLEM,
    ProblemExample,
    describe_problem_responses,
)
from emi_copilot.dtos.problem_details_dto import CustomerProblemDetailsResponse

CUSTOMER_OPERATION_NOTE = (
    "Customer endpoint, opened from the shop's QR on the customer's own phone; the shop never "
    "sees what is sent here. Money is integer paise, shares are integer basis points, errors "
    "are application/problem+json. "
)
SESSION_TOKEN_NOTE = "Needs the X-Customer-Session-Token header. "  # noqa: S105 - prose

CUSTOMER_QR_TOKEN_INVALID_PROBLEM = ProblemExample(
    401,
    "CUSTOMER_QR_TOKEN_INVALID",
    "QR code not valid",
    "This QR code is not valid; ask the shop for a new QR.",
    "The QR token is unknown, already used, replaced, expired, or its sale is no longer open; "
    "the shop can show a new QR.",
)
CUSTOMER_SESSION_TOKEN_INVALID_PROBLEM = ProblemExample(
    401,
    "CUSTOMER_SESSION_TOKEN_INVALID",
    "Customer session not valid",
    "This session link is not valid; ask the shop for a new QR.",
    "The session token is missing, opens no session, or the session or its sale has ended.",
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
    "Consent for this sale was already given.",
    "The plan for this sale is already agreed, so the steps before consent are closed; a new "
    "Idempotency-Key cannot record a second consent.",
)
CONSENT_NOT_GIVEN_PROBLEM = ProblemExample(
    409,
    "CONSENT_NOT_GIVEN",
    "Consent not given yet",
    "There is no receipt until the plan is agreed.",
    "The plan has not been agreed to yet.",
)
CONSENT_CHAIN_CONFLICT_PROBLEM = ProblemExample(
    409,
    "CONSENT_RECORD_CHAIN_CONFLICT",
    "Consent could not be recorded yet",
    "Another consent was being recorded at the same moment; send the same request again.",
    "Another consent took the evidence chain's head at the same moment; retry with the same "
    "Idempotency-Key.",
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
    "The code does not match; attemptsRemaining says how many more tries it allows.",
    attempts_remaining=2,
)
OTP_EXPIRED_PROBLEM = ProblemExample(
    422,
    "OTP_EXPIRED",
    "One-time code expired",
    "This code has expired; request a new code.",
    "The code is past its 5-minute lifetime or its 3 tries are used; request a new one.",
)
CUSTOMER_CONTACT_UNAVAILABLE_PROBLEM = ProblemExample(
    422,
    "CUSTOMER_CONTACT_UNAVAILABLE",
    "Phone number not available",
    "No phone number is known for this sale; ask the shop for help.",
    "The payment side knows no phone number for this sale, so no code can be sent.",
)
OFFER_NOT_QUOTED_PROBLEM = ProblemExample(
    404,
    "OFFER_NOT_FOUND",
    "Offer not found",
    "The offer is not quoted for this item and price.",
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
    "This plan is not offered for the session's item.",
    "The offer is not one quoted for the session's item at the sale price.",
)
SHOWN_PLAN_CHANGED_PROBLEM = ProblemExample(
    409,
    "SHOWN_PLAN_CHANGED",
    "Plan figures changed",
    "The plan figures changed; show the plans again.",
    "A fresh quote no longer matches the monthly or total shown; nothing was recorded.",
)
OTP_RESEND_NOT_YET_AVAILABLE_PROBLEM = ProblemExample(
    429,
    "OTP_RESEND_NOT_YET_AVAILABLE",
    "New one-time code not available yet",
    "A new code can be sent once the wait is over.",
    "The current code can be replaced 30 seconds after it was sent; Retry-After says when.",
)
QR_EXCHANGE_RATE_LIMITED_PROBLEM = ProblemExample(
    429,
    "RATE_LIMITED",
    "Too many requests",
    "Too many QR exchanges from this client; try again after Retry-After.",
    "This client exchanged too many QR codes in this minute.",
)
OTP_REQUEST_RATE_LIMITED_PROBLEM = ProblemExample(
    429,
    "RATE_LIMITED",
    "Too many requests",
    "Too many one-time code requests for this session; try again after Retry-After.",
    "This phone asked for too many codes for the session in this window.",
)
CONSENT_RATE_LIMITED_PROBLEM = ProblemExample(
    429,
    "RATE_LIMITED",
    "Too many requests",
    "Too many consent attempts for this session; try again after Retry-After.",
    "This phone made too many consent attempts for the session in this window.",
)

SESSION_PROBLEMS = (
    CUSTOMER_SESSION_TOKEN_INVALID_PROBLEM,
    CUSTOMER_SESSION_NOT_FOUND_PROBLEM,
    REQUEST_VALIDATION_PROBLEM,
)
QUOTING_PROBLEMS = (CUSTOMER_GATEWAY_UNAVAILABLE_PROBLEM, GATEWAY_TIMEOUT_PROBLEM)


def describe_customer_problem_responses(*problem_examples: ProblemExample) -> dict[int | str, Any]:
    """Documents a customer operation's problems with the customer problem schema."""
    return describe_problem_responses(
        *problem_examples, problem_model=CustomerProblemDetailsResponse
    )
