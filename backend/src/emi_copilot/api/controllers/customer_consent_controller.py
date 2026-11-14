"""POST .../consent/otp and POST .../consent: the one-time code and consent as evidence (C9)."""

from typing import Annotated

from fastapi import APIRouter, Header, Request, Response

from emi_copilot.api.controllers.customer_flow_service_providers import (
    CustomerConsentServiceDependency,
    CustomerSessionCredentialsDependency,
)
from emi_copilot.api.controllers.customer_problem_examples import (
    BUDGET_NOT_CONFIRMED_PROBLEM,
    CONSENT_ALREADY_GIVEN_PROBLEM,
    IDEMPOTENCY_KEY_REUSED_PROBLEM,
    OFFER_NOT_QUOTED_PROBLEM,
    OTP_EXPIRED_PROBLEM,
    OTP_INCORRECT_PROBLEM,
    OTP_NOT_REQUESTED_PROBLEM,
    PLAN_SELECTION_PROBLEMS,
    QUOTING_PROBLEMS,
    SESSION_PROBLEMS,
    SESSION_TOKEN_NOTE,
    STUB_OPERATION_NOTE,
)
from emi_copilot.api.controllers.customer_receipt_controller import (
    GET_CUSTOMER_RECEIPT_ROUTE_NAME,
)
from emi_copilot.api.controllers.customer_response_examples import (
    CONSENT_RESPONSE_EXAMPLE,
    OTP_CHALLENGE_RESPONSE_EXAMPLE,
)
from emi_copilot.api.openapi_documentation import (
    MALFORMED_REQUEST_PROBLEM,
    describe_problem_responses,
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
        STUB_OPERATION_NOTE + SESSION_TOKEN_NOTE + "Sends a 6-digit code to the customer's "
        "phone (the stub code is 123456; nothing is sent). The code lasts 5 minutes; a new one "
        "can be asked for after 30 seconds, which restarts the lifetime."
    ),
    response_description="Where the code went and when it ends.",
    responses={
        200: {"content": {"application/json": {"example": OTP_CHALLENGE_RESPONSE_EXAMPLE}}},
        **describe_problem_responses(*SESSION_PROBLEMS),
    },
)
def request_consent_one_time_code(
    credentials: CustomerSessionCredentialsDependency,
    consent_service: CustomerConsentServiceDependency,
) -> OtpChallengeResponse:
    """Issues the one-time code for the session."""
    return OtpChallengeResponse.from_challenge(consent_service.request_one_time_code(credentials))


@customer_consent_router.post(
    "/customer-sessions/{customerSessionId}/consent",
    status_code=201,
    summary="Agree to the chosen plan with the one-time code",
    description=(
        STUB_OPERATION_NOTE + SESSION_TOKEN_NOTE + "Names the exact selection shown on C9: "
        "the offer, the product (null for the session's item, or the cheaper model) and the down "
        "payment (0, or exactly the one suggested). It is re-quoted server-side; if the shown "
        "monthly or total no longer match, the answer is 409 SHOWN_PLAN_CHANGED and nothing is "
        "recorded. The exact selection is stored as evidence, once per session. The same "
        "Idempotency-Key and selection return the original 201 response (the code is not part "
        "of the comparison). No payment link is made: the shop takes payment on Paytm. Location "
        "points at the receipt. Needs the confirmed budget and a requested, unexpired, matching "
        "code."
    ),
    response_description="The consent was recorded (or this is the replay of it).",
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
        **describe_problem_responses(
            MALFORMED_REQUEST_PROBLEM,
            *SESSION_PROBLEMS,
            OFFER_NOT_QUOTED_PROBLEM,
            BUDGET_NOT_CONFIRMED_PROBLEM,
            CONSENT_ALREADY_GIVEN_PROBLEM,
            OTP_NOT_REQUESTED_PROBLEM,
            OTP_INCORRECT_PROBLEM,
            OTP_EXPIRED_PROBLEM,
            IDEMPOTENCY_KEY_REUSED_PROBLEM,
            *PLAN_SELECTION_PROBLEMS,
            *QUOTING_PROBLEMS,
        ),
    },
)
def give_customer_consent(  # noqa: PLR0913 - body, key, session, request, response, service
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
    request: Request,
    response: Response,
    consent_service: CustomerConsentServiceDependency,
) -> ConsentResponse:
    """Records consent for the body and key, and points Location at the receipt."""
    recorded_consent = consent_service.give_consent(
        credentials, consent_request.to_command(idempotency_key)
    )
    response.headers["Location"] = str(
        request.app.url_path_for(
            GET_CUSTOMER_RECEIPT_ROUTE_NAME, customerSessionId=credentials.customer_session_id
        )
    )
    return ConsentResponse.from_recorded_consent(recorded_consent)
