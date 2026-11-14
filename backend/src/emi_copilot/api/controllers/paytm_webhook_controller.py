"""POST /api/v1/webhooks/paytm: payment notifications, verified before any field is read.

Order of work, and why:
0. Count the request against the per-client webhook limit (429), before anything is read.
1. Refuse any media type but application/x-www-form-urlencoded (415; ADR 0002 [Verify]).
2. Refuse a declared or actual body above 16 KiB (413) while streaming, so a large post cannot
   exhaust memory; nothing is buffered past the limit.
3. Parse the body into raw text keys and values only; nothing is interpreted. A body that is
   not form data, or repeats a field name (which would make the signed set ambiguous), is 400.
4. Hand the untrusted fields to the service, which verifies the signature over all of them
   before reading any; a bad signature is audited there and answered 401.
5. Answer 202 with no body for every verified notification, repeats and unknown orders too.
The body is never logged: it holds the signature and may hold personal data.
"""

from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from emi_copilot.api.dependencies import PaymentStatusServiceDependency
from emi_copilot.api.openapi_documentation import (
    GATEWAY_FAILURE_PROBLEMS,
    MALFORMED_REQUEST_PROBLEM,
    ProblemExample,
    describe_problem_responses,
)
from emi_copilot.api.rate_limiting import enforce_payment_webhook_rate_limit
from emi_copilot.dtos.webhook_notification_dtos import build_unverified_notification

paytm_webhook_router = APIRouter(tags=["webhooks"])

MAXIMUM_WEBHOOK_BODY_SIZE_IN_BYTES = 16 * 1024
# A real notification has a few dozen fields; far more is not a notification.
MAXIMUM_WEBHOOK_FIELD_COUNT = 200
FORM_MEDIA_TYPE = "application/x-www-form-urlencoded"
WEBHOOK_PROBLEMS = (
    ProblemExample(
        401,
        "WEBHOOK_SIGNATURE_INVALID",
        "Webhook rejected",
        "The notification checksum is missing or does not match its fields.",
        "The signature is missing or does not match the fields; the rejection is audited.",
    ),
    ProblemExample(
        413,
        "REQUEST_BODY_TOO_LARGE",
        "Request body too large",
        "The webhook body exceeds 16384 bytes.",
        "The body is larger than 16 KiB.",
    ),
    ProblemExample(
        429,
        "RATE_LIMITED",
        "Too many requests",
        "Too many webhook requests from this client; try again after Retry-After.",
        "The client sent too many notifications in this minute (a generous limit).",
    ),
    ProblemExample(
        415,
        "UNSUPPORTED_MEDIA_TYPE",
        "Unsupported media type",
        "The webhook body must be application/x-www-form-urlencoded.",
        "The body is not form-encoded.",
    ),
)


def _body_too_large_error() -> HTTPException:
    """Gives the 413 error for a body above the webhook limit."""
    return HTTPException(
        status_code=413,
        detail=f"The webhook body exceeds {MAXIMUM_WEBHOOK_BODY_SIZE_IN_BYTES} bytes.",
    )


def require_form_media_type(request: Request) -> None:
    """Raises 415 unless the body is declared form-encoded; parameters such as charset are fine."""
    media_type = request.headers.get("content-type", "").split(";", maxsplit=1)[0]
    if media_type.strip().lower() != FORM_MEDIA_TYPE:
        raise HTTPException(status_code=415, detail=f"The webhook body must be {FORM_MEDIA_TYPE}.")


async def read_body_within_limit(request: Request) -> bytes:
    """Reads the body, refusing with 413 once the declared or received size passes the limit."""
    declared_length = request.headers.get("content-length", "")
    if declared_length.isdigit() and int(declared_length) > MAXIMUM_WEBHOOK_BODY_SIZE_IN_BYTES:
        raise _body_too_large_error()
    received_body = bytearray()
    async for body_chunk in request.stream():
        received_body.extend(body_chunk)
        if len(received_body) > MAXIMUM_WEBHOOK_BODY_SIZE_IN_BYTES:
            raise _body_too_large_error()
    return bytes(received_body)


def parse_raw_form_fields(body: bytes) -> dict[str, str]:
    """Splits a form body into raw text keys and values; nothing is interpreted or logged."""
    try:
        field_pairs = parse_qsl(
            body.decode("utf-8"),
            keep_blank_values=True,
            strict_parsing=True,
            max_num_fields=MAXIMUM_WEBHOOK_FIELD_COUNT,
        )
    except ValueError as parse_error:
        raise HTTPException(
            status_code=400, detail="The webhook body is not valid UTF-8 form data."
        ) from parse_error
    raw_fields = dict(field_pairs)
    if len(raw_fields) != len(field_pairs):
        raise HTTPException(status_code=400, detail="The webhook body repeats a field name.")
    return raw_fields


@paytm_webhook_router.post(
    "/webhooks/paytm",
    status_code=202,
    dependencies=[Depends(enforce_payment_webhook_rate_limit)],
    summary="Receive a payment notification from the gateway",
    description=(
        "Called by the payment gateway, not by our apps. The body is form-encoded key/value "
        "text [Verify] of at most 16 KiB. Its signature (CHECKSUMHASH) is verified over every "
        "field before any field is read; a mismatch answers 401 and is audited. A verified "
        "notification answers 202 with no body, also when it repeats an earlier one (no extra "
        "effect) or names an order that is not ours. Authenticated by the signature only; no "
        "credentials (ADR 0009). A generous per-client limit applies (429 with Retry-After)."
    ),
    response_class=Response,
    response_description="Verified and applied; no body.",
    responses=describe_problem_responses(
        MALFORMED_REQUEST_PROBLEM, *WEBHOOK_PROBLEMS, *GATEWAY_FAILURE_PROBLEMS
    ),
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                FORM_MEDIA_TYPE: {
                    "schema": {"type": "object", "additionalProperties": {"type": "string"}},
                    "example": {
                        "ORDERID": "01JD5Z0Q8M6X3V2N7B4C9K1T0A",
                        "STATUS": "TXN_SUCCESS",
                        "CHECKSUMHASH": "signature-over-every-other-field",
                    },
                }
            },
        }
    },
)
async def receive_paytm_webhook(
    request: Request, payment_status_service: PaymentStatusServiceDependency
) -> Response:
    """Checks media type and size, parses raw fields, then lets the service verify and apply."""
    require_form_media_type(request)
    body = await read_body_within_limit(request)
    notification = build_unverified_notification(parse_raw_form_fields(body))
    await run_in_threadpool(payment_status_service.apply_webhook, notification)
    return Response(status_code=202)
