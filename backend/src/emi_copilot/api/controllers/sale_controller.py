"""The merchant's sales: start one, list today's, read one and re-issue its customer QR code."""

from typing import Annotated

from fastapi import APIRouter, Body, Header, Path, Query, Request, Response

from emi_copilot.api.controllers.sale_documentation import (
    COUNTER_SALES_EXAMPLE,
    CUSTOMER_QR_EXAMPLE,
    IDEMPOTENCY_KEY_DESCRIPTION,
    IDEMPOTENCY_KEY_REUSED_PROBLEM,
    PRODUCT_NOT_FOUND_PROBLEM,
    READY_TO_PAY_SALE_DETAIL_EXAMPLE,
    SALE_NOT_FOUND_PROBLEM,
    SALE_STATE_CONFLICT_PROBLEM,
    SESSION_CODES_EXHAUSTED_PROBLEM,
    START_SALE_REQUEST_EXAMPLE,
    STARTED_SALE_EXAMPLE,
)
from emi_copilot.api.merchant_authentication import CurrentMerchant
from emi_copilot.api.openapi_documentation import (
    MALFORMED_REQUEST_PROBLEM,
    MERCHANT_AUTHENTICATION_PROBLEM,
    MERCHANT_BEARER_NOTE,
    REQUEST_VALIDATION_PROBLEM,
    describe_problem_responses,
)
from emi_copilot.api.sale_dependencies import (
    GetSaleServiceDependency,
    IssueQrTokenServiceDependency,
    ListCounterSalesServiceDependency,
    StartSaleServiceDependency,
)
from emi_copilot.dtos.payment_link_dtos import (
    IDEMPOTENCY_KEY_PATTERN,
    MINIMUM_IDEMPOTENCY_KEY_LENGTH,
)
from emi_copilot.dtos.sale_dtos import (
    CounterSalesResponse,
    CustomerQrResponse,
    SaleDetailResponse,
    SalesQuery,
    StartSaleRequest,
)
from emi_copilot.dtos.wire_types import MAXIMUM_IDENTIFIER_LENGTH, VISIBLE_ASCII_PATTERN
from emi_copilot.services.sale_views import MAXIMUM_SALE_IDEMPOTENCY_KEY_LENGTH

sale_router = APIRouter(tags=["sales"])

GET_SALE_ROUTE_NAME = "get_sale"
# Answers that carry a QR token must never sit in a cache.
NO_STORE_HEADERS = {"Cache-Control": "no-store", "Pragma": "no-cache"}
SaleIdPath = Annotated[
    str,
    Path(
        alias="saleId",
        min_length=1,
        max_length=MAXIMUM_IDENTIFIER_LENGTH,
        pattern=VISIBLE_ASCII_PATTERN,
        description="The sale id returned by POST /api/v1/sales.",
        examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0F"],
    ),
]
LOCATION_AND_NO_STORE_HEADERS = {
    "Location": {"description": "The sale's URL.", "schema": {"type": "string"}},
    "Cache-Control": {"description": "Always no-store.", "schema": {"type": "string"}},
}


def build_sale_location(request: Request, sale_id: str) -> str:
    """Gives the URL of one sale, for the Location header."""
    return str(request.app.url_path_for(GET_SALE_ROUTE_NAME, saleId=sale_id))


@sale_router.post(
    "/sales",
    status_code=201,
    summary="Start a sale and get its customer QR code",
    description=(
        "Starts a sale of one catalogue product at its list price (the price at the counter "
        "cannot be changed). The sale is CHOOSING and gets a 4-digit session code unique among "
        "the shop's open sales, and qr holds the URL to show as a QR code, valid for 15 minutes "
        "by default. An optional Idempotency-Key makes a retry return the same sale. Location "
        "points at the sale; the answer is never cached. " + MERCHANT_BEARER_NOTE
    ),
    response_description="The sale was started (or this is the replay of its start).",
    responses={
        201: {
            "content": {"application/json": {"example": STARTED_SALE_EXAMPLE}},
            "headers": LOCATION_AND_NO_STORE_HEADERS,
        },
        **describe_problem_responses(
            MALFORMED_REQUEST_PROBLEM,
            REQUEST_VALIDATION_PROBLEM,
            IDEMPOTENCY_KEY_REUSED_PROBLEM,
            MERCHANT_AUTHENTICATION_PROBLEM,
            PRODUCT_NOT_FOUND_PROBLEM,
            SESSION_CODES_EXHAUSTED_PROBLEM,
        ),
    },
)
def start_sale(  # noqa: PLR0913 - mostly Annotated request parameter declarations
    *,
    start_sale_request: Annotated[
        StartSaleRequest,
        Body(
            openapi_examples={
                "phone-128-gb": {
                    "summary": "The ₹22,000 phone",
                    "value": START_SALE_REQUEST_EXAMPLE,
                }
            }
        ),
    ],
    current_merchant: CurrentMerchant,
    request: Request,
    response: Response,
    start_sale_service: StartSaleServiceDependency,
    idempotency_key: Annotated[
        str | None,
        Header(
            alias="Idempotency-Key",
            min_length=MINIMUM_IDEMPOTENCY_KEY_LENGTH,
            max_length=MAXIMUM_SALE_IDEMPOTENCY_KEY_LENGTH,
            pattern=IDEMPOTENCY_KEY_PATTERN,
            description=IDEMPOTENCY_KEY_DESCRIPTION,
            examples=["5f0c2a2e-6d1b-4c55-9a43-3f1b2f7f8e11"],
        ),
    ] = None,
) -> SaleDetailResponse:
    """Starts the sale for the signed-in shop and points Location at it."""
    started_sale = start_sale_service.start_sale(
        current_merchant, start_sale_request.to_command(idempotency_key)
    )
    response.headers.update(NO_STORE_HEADERS)
    response.headers["Location"] = build_sale_location(request, started_sale.counter_sale.sale.id)
    return SaleDetailResponse.from_started_sale(started_sale)


@sale_router.get(
    "/sales",
    summary="List today's sales at the counter",
    description=(
        "With view=counter: the shop's sales started today in the shop's time zone (IST), "
        "newest first, without expired ones. A sale still CHOOSING an hour after it started is "
        "expired first. Each sale shows only its code, product, price, status and, once the "
        "customer agreed, the chosen plan; never any customer detail. " + MERCHANT_BEARER_NOTE
    ),
    response_description="Today's sales, newest first.",
    responses={
        200: {"content": {"application/json": {"example": COUNTER_SALES_EXAMPLE}}},
        **describe_problem_responses(REQUEST_VALIDATION_PROBLEM, MERCHANT_AUTHENTICATION_PROBLEM),
    },
)
def list_sales(
    # Validated to view=counter, the only list in Layer 2; later views will dispatch on it.
    sales_query: Annotated[SalesQuery, Query()],  # noqa: ARG001
    current_merchant: CurrentMerchant,
    list_counter_sales_service: ListCounterSalesServiceDependency,
) -> CounterSalesResponse:
    """Lists the signed-in shop's counter sales for today."""
    return CounterSalesResponse.from_counter_sales(
        list_counter_sales_service.list_counter_sales(current_merchant)
    )


@sale_router.get(
    "/sales/{saleId}",
    name=GET_SALE_ROUTE_NAME,
    summary="Read one sale",
    description=(
        "Gives one of the shop's sales as it stands now (expired first if overdue). qr is "
        "always null here: raw QR tokens are never stored, so ask POST /api/v1/sales/{saleId}/"
        "qr-tokens for a new one. Another shop's sale answers 404. " + MERCHANT_BEARER_NOTE
    ),
    response_description="The sale.",
    responses={
        200: {"content": {"application/json": {"example": READY_TO_PAY_SALE_DETAIL_EXAMPLE}}},
        **describe_problem_responses(
            REQUEST_VALIDATION_PROBLEM, MERCHANT_AUTHENTICATION_PROBLEM, SALE_NOT_FOUND_PROBLEM
        ),
    },
)
def get_sale(
    sale_id: SaleIdPath,
    current_merchant: CurrentMerchant,
    get_sale_service: GetSaleServiceDependency,
) -> SaleDetailResponse:
    """Reads the sale for the signed-in shop; there is never a QR link in this answer."""
    return SaleDetailResponse.from_counter_sale_and_link(
        get_sale_service.get_sale(current_merchant, sale_id), None
    )


@sale_router.post(
    "/sales/{saleId}/qr-tokens",
    status_code=201,
    summary="Issue a new customer QR code for a sale",
    description=(
        "Issues a fresh QR code while the sale is CHOOSING, which voids the previous one; any "
        "other status answers 409 SALE_STATE_CONFLICT. Location points at the sale; the answer "
        "is never cached. " + MERCHANT_BEARER_NOTE
    ),
    response_description="The new QR code.",
    responses={
        201: {
            "content": {"application/json": {"example": CUSTOMER_QR_EXAMPLE}},
            "headers": LOCATION_AND_NO_STORE_HEADERS,
        },
        **describe_problem_responses(
            REQUEST_VALIDATION_PROBLEM,
            MERCHANT_AUTHENTICATION_PROBLEM,
            SALE_NOT_FOUND_PROBLEM,
            SALE_STATE_CONFLICT_PROBLEM,
        ),
    },
)
def issue_qr_token(
    sale_id: SaleIdPath,
    current_merchant: CurrentMerchant,
    request: Request,
    response: Response,
    issue_qr_token_service: IssueQrTokenServiceDependency,
) -> CustomerQrResponse:
    """Re-issues the sale's QR code and points Location at the sale."""
    qr_link = issue_qr_token_service.issue_qr_token(current_merchant, sale_id)
    response.headers.update(NO_STORE_HEADERS)
    response.headers["Location"] = build_sale_location(request, sale_id)
    return CustomerQrResponse.from_link(qr_link)
