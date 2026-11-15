"""POST .../consent/otp and POST .../consent: the one-time code and consent as evidence (C9)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response

from emi_copilot.api.controllers.customer_problem_examples import (
    BUDGET_NOT_CONFIRMED_PROBLEM,
    CONSENT_ALREADY_GIVEN_PROBLEM,
    CONSENT_CHAIN_CONFLICT_PROBLEM,
    CONSENT_RATE_LIMITED_PROBLEM,
    CUSTOMER_CONTACT_UNAVAILABLE_PROBLEM,
    CUSTOMER_OPERATION_NOTE,
    IDEMPOTENCY_KEY_REUSED_PROBLEM,
    INVALID_PLAN_SELECTION_PROBLEM,
    OTP_EXPIRED_PROBLEM,
    OTP_INCORRECT_PROBLEM,
    OTP_NOT_REQUESTED_PROBLEM,
    OTP_REQUEST_RATE_LIMITED_PROBLEM,
    OTP_RESEND_NOT_YET_AVAILABLE_PROBLEM,
    QUOTING_PROBLEMS,
    SESSION_PROBLEMS,
    SESSION_TOKEN_NOTE,
    SHOWN_PLAN_CHANGED_PROBLEM,
    describe_customer_problem_responses,
)
from emi_copilot.api.controllers.customer_receipt_controller import (
    GET_CUSTOMER_RECEIPT_ROUTE_NAME,
)
from emi_copilot.api.controllers.customer_response_examples import (
    CONSENT_RESPONSE_EXAMPLE,
    OTP_CHALLENGE_RESPONSE_EXAMPLE,
)
from emi_copilot.api.customer_dependencies import (
    ConsentOtpServiceDependency,
    CustomerConsentServiceDependency,
)
from emi_copilot.api.customer_request_context import (
    CustomerLanguageDependency,
    CustomerSessionCredentialsDependency,
)
from emi_copilot.api.openapi_documentation import MALFORMED_REQUEST_PROBLEM
from emi_copilot.api.rate_limiting import (
    enforce_consent_otp_request_rate_limit,
    enforce_customer_consent_rate_limit,
)
from emi_copilot.dtos.customer_consent_dtos import (
    ConsentResponse,
    GiveConsentRequest,
    OtpChallengeResponse,
)
from emi_copilot.dtos.payment_link_dtos import (
    IDEMPOTENCY_KEY_HEADER_DESCRIPTION,
    IDEMPOTENCY_KEY_PATTERN,
    MINIMUM_IDEMPOTENCY_KEY_LENGTH,
)
from emi_copilot.services.payment_handoff_types import MAXIMUM_IDEMPOTENCY_KEY_LENGTH

customer_consent_router = APIRouter(tags=["customer consent"])


@customer_consent_router.post(
    "/customer-sessions/{customerSessionId}/consent/otp",
    summary="Send the one-time code for consent",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + "Sends a 6-digit code to the phone the "
        "payment side knows for this sale (a labelled Mock in this build, ending 42; the demo "
        "code is fixed and nothing is sent). The code lasts 5 minutes and allows 3 tries. A new "
        "code can be asked for 30 seconds after the last (429 with Retry-After before then), or "
        "at once when the last one expired or its tries are used. Limited per client and "
        "session. Needs the confirmed budget and a plan not yet agreed."
    ),
    response_description="Where the code went, when it ends and how many tries it allows.",
    dependencies=[Depends(enforce_consent_otp_request_rate_limit)],
    responses={
        200: {"content": {"application/json": {"example": OTP_CHALLENGE_RESPONSE_EXAMPLE}}},
        **describe_customer_problem_responses(
            *SESSION_PROBLEMS,
            BUDGET_NOT_CONFIRMED_PROBLEM,
            CONSENT_ALREADY_GIVEN_PROBLEM,
            CUSTOMER_CONTACT_UNAVAILABLE_PROBLEM,
            OTP_RESEND_NOT_YET_AVAILABLE_PROBLEM,
            OTP_REQUEST_RATE_LIMITED_PROBLEM,
        ),
    },
)
def request_consent_one_time_code(
    credentials: CustomerSessionCredentialsDependency,
    otp_service: ConsentOtpServiceDependency,
) -> OtpChallengeResponse:
    """Sends a new one-time code for the session."""
    return OtpChallengeResponse.from_challenge(otp_service.request_otp(credentials))


@customer_consent_router.post(
    "/customer-sessions/{customerSessionId}/consent",
    status_code=201,
    summary="Agree to the chosen plan with the one-time code",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + "Names the plan (an offer on the "
        "session's item at the sale price) and the monthly amount and total shown on C9. It is "
        "re-quoted server-side; if the figures no longer match, the answer is 409 "
        "SHOWN_PLAN_CHANGED and nothing is recorded. A wrong code answers 422 OTP_INCORRECT "
        "with attemptsRemaining; after the last try the code is spent (OTP_EXPIRED). The plan "
        "is stored once per sale as hash-chained evidence, in the language of Accept-Language, "
        "and the shop sees the sale READY_TO_PAY with this plan. The same Idempotency-Key and "
        "plan return the original 201 response (the code is not part of the comparison). No "
        "payment link is made: the shop takes payment on Paytm. Limited per client and "
        "session. Location points at the receipt."
    ),
    response_description="The consent was recorded (or this is the replay of it).",
    dependencies=[Depends(enforce_customer_consent_rate_limit)],
    responses={
        201: {
            "content": {"application/json": {"example": CONSENT_RESPONSE_EXAMPLE}},
            "headers": {
                "Location": {
                    "description": "The receipt URL of this session.",
                    "schema": {"type": "string"},
                }
            },
        },
        **describe_customer_problem_responses(
            MALFORMED_REQUEST_PROBLEM,
            *SESSION_PROBLEMS,
            INVALID_PLAN_SELECTION_PROBLEM,
            BUDGET_NOT_CONFIRMED_PROBLEM,
            CONSENT_ALREADY_GIVEN_PROBLEM,
            CONSENT_CHAIN_CONFLICT_PROBLEM,
            SHOWN_PLAN_CHANGED_PROBLEM,
            OTP_NOT_REQUESTED_PROBLEM,
            OTP_INCORRECT_PROBLEM,
            OTP_EXPIRED_PROBLEM,
            IDEMPOTENCY_KEY_REUSED_PROBLEM,
            CUSTOMER_CONTACT_UNAVAILABLE_PROBLEM,
            CONSENT_RATE_LIMITED_PROBLEM,
            *QUOTING_PROBLEMS,
        ),
    },
)
def give_customer_consent(  # noqa: PLR0913 - body, key, session, language, request, response, service
    consent_request: GiveConsentRequest,
    *,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=MINIMUM_IDEMPOTENCY_KEY_LENGTH,
            max_length=MAXIMUM_IDEMPOTENCY_KEY_LENGTH,
            pattern=IDEMPOTENCY_KEY_PATTERN,
            description=IDEMPOTENCY_KEY_HEADER_DESCRIPTION,
            examples=["5f0c2a2e-6d1b-4c55-9a43-3f1b2f7f8e11"],
        ),
    ],
    credentials: CustomerSessionCredentialsDependency,
    language: CustomerLanguageDependency,
    request: Request,
    response: Response,
    consent_service: CustomerConsentServiceDependency,
) -> ConsentResponse:
    """Records consent for the body and key, and points Location at the receipt."""
    consent_record = consent_service.give_consent(
        credentials, consent_request.to_command(idempotency_key, language)
    )
    response.headers["Location"] = str(
        request.app.url_path_for(
            GET_CUSTOMER_RECEIPT_ROUTE_NAME, customerSessionId=credentials.customer_session_id
        )
    )
    return ConsentResponse.from_consent_record(consent_record)
