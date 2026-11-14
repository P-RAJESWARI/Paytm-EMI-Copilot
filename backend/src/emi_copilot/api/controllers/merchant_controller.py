"""POST /api/v1/merchants/pairing and GET /api/v1/merchants/me: device pairing and profile."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response

from emi_copilot.api.dependencies import PairDeviceServiceDependency
from emi_copilot.api.merchant_authentication import CurrentMerchant
from emi_copilot.api.openapi_documentation import (
    MALFORMED_REQUEST_PROBLEM,
    MERCHANT_AUTHENTICATION_PROBLEM,
    MERCHANT_BEARER_NOTE,
    REQUEST_VALIDATION_PROBLEM,
    ProblemExample,
    describe_problem_responses,
)
from emi_copilot.api.rate_limiting import enforce_pairing_rate_limit
from emi_copilot.dtos.merchant_dtos import (
    DevicePairingResponse,
    MerchantProfileResponse,
    PairDeviceRequest,
)

merchant_router = APIRouter(tags=["merchants"])

GET_CURRENT_MERCHANT_ROUTE_NAME = "get_current_merchant"
MERCHANT_PROFILE_EXAMPLE = {
    "merchantId": "01JD5Z0Q8M6X3V2N7B4C9K1T0C",
    "shopId": "RAVI-0193",
    "shopName": "Ravi Electronics",
    "deviceLabel": "Counter tablet 1",
}
DEVICE_PAIRING_RESPONSE_EXAMPLE = {
    "accessToken": "example-opaque-bearer-token-shown-once",
    "tokenType": "Bearer",
    "expiresAt": "2026-11-15T09:30:00Z",
    "merchant": MERCHANT_PROFILE_EXAMPLE,
}
PAIRING_PROBLEMS = (
    ProblemExample(
        401,
        "INVALID_PAIRING_CREDENTIALS",
        "Shop id or PIN not recognised",
        "The shop id and PIN do not match a shop.",
        "The shop id and PIN do not match; an unknown shop and a wrong PIN get this same answer.",
    ),
    ProblemExample(
        429,
        "PAIRING_TEMPORARILY_LOCKED",
        "Pairing temporarily locked",
        "Pairing is locked after repeated wrong PINs; try again after Retry-After.",
        "After 5 wrong PINs in a row the shop is locked for 15 minutes, even for the right PIN; "
        "or this client sent too many pairing requests (RATE_LIMITED). Retry-After says when.",
    ),
    ProblemExample(
        429,
        "RATE_LIMITED",
        "Too many requests",
        "Too many pairing requests from this client; try again after Retry-After.",
        "",
    ),
)
NO_STORE_HEADERS = {"Cache-Control": "no-store", "Pragma": "no-cache"}


@merchant_router.post(
    "/merchants/pairing",
    status_code=201,
    summary="Pair a counter device with the shop id and PIN",
    description=(
        "Trades the shop id and the shop's 6-digit pairing PIN for a bearer token for this "
        "device. The token is shown once and only its hash is stored; it lasts 12 hours by "
        "default. This endpoint needs no credentials and is rate-limited per client address. "
        "An unknown shop and a wrong PIN get the same 401; 5 wrong PINs in a row lock the shop "
        "for 15 minutes (429 with Retry-After). Location points at the signed-in profile. The "
        "answer is never cached (Cache-Control: no-store)."
    ),
    response_description="The device is paired.",
    dependencies=[Depends(enforce_pairing_rate_limit)],
    responses={
        201: {
            "content": {"application/json": {"example": DEVICE_PAIRING_RESPONSE_EXAMPLE}},
            "headers": {
                "Location": {
                    "description": "The signed-in merchant profile.",
                    "schema": {"type": "string"},
                },
                "Cache-Control": {"description": "Always no-store.", "schema": {"type": "string"}},
            },
        },
        **describe_problem_responses(
            MALFORMED_REQUEST_PROBLEM, REQUEST_VALIDATION_PROBLEM, *PAIRING_PROBLEMS
        ),
    },
)
def pair_device(
    pairing_request: Annotated[
        PairDeviceRequest,
        Body(
            openapi_examples={
                "demo-shop": {
                    "summary": "The demo shop (PIN set by the seed)",
                    "value": {"shopId": "RAVI-0193", "pin": "<6-digit PIN>"},
                }
            }
        ),
    ],
    request: Request,
    response: Response,
    pair_device_service: PairDeviceServiceDependency,
) -> DevicePairingResponse:
    """Pairs the device, marks the answer uncacheable and points Location at the profile."""
    result = pair_device_service.pair_device(pairing_request.to_command())
    response.headers.update(NO_STORE_HEADERS)
    response.headers["Location"] = str(request.app.url_path_for(GET_CURRENT_MERCHANT_ROUTE_NAME))
    return DevicePairingResponse.from_result(result)


@merchant_router.get(
    "/merchants/me",
    name=GET_CURRENT_MERCHANT_ROUTE_NAME,
    summary="Read the signed-in shop and device",
    description=(
        "Gives the shop and device the bearer token signs in, for the merchant app's header. "
        + MERCHANT_BEARER_NOTE
    ),
    response_description="The signed-in shop and device.",
    responses={
        200: {"content": {"application/json": {"example": MERCHANT_PROFILE_EXAMPLE}}},
        **describe_problem_responses(MERCHANT_AUTHENTICATION_PROBLEM),
    },
)
def get_current_merchant(current_merchant: CurrentMerchant) -> MerchantProfileResponse:
    """Converts the signed-in principal to the profile shape."""
    return MerchantProfileResponse.from_principal(current_merchant)
