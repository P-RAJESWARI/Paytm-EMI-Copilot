"""MockCustomerSimulator endpoints: the demo's stand-in for the customer's phone (rules 9, 10).

Mounted only when MOCK_CUSTOMER_SIMULATOR_ENABLED=true (never in paytm mode, which settings
refuse), announced in the startup log, and left out of openapi.json, so no generated client
can call it. Each call needs the shop's bearer token and touches only that shop's sales.
"""

from typing import Annotated

from fastapi import APIRouter, Body, Path, Response

from emi_copilot.api.controllers.sale_controller import SaleIdPath
from emi_copilot.api.merchant_authentication import CurrentMerchant
from emi_copilot.api.sale_dependencies import MockCustomerSimulatorServiceDependency
from emi_copilot.dtos.mock_customer_simulator_dtos import MockAgreedPlanRequest
from emi_copilot.dtos.sale_dtos import SaleSummaryResponse
from emi_copilot.dtos.wire_types import MAXIMUM_IDENTIFIER_LENGTH, VISIBLE_ASCII_PATTERN

MOCK_CUSTOMER_SIMULATOR_PATH_PREFIX = "/mock-customer-simulator"

mock_customer_simulator_router = APIRouter(
    prefix=MOCK_CUSTOMER_SIMULATOR_PATH_PREFIX,
    tags=["mock customer simulator"],
    include_in_schema=False,
)


@mock_customer_simulator_router.post("/sales/{saleId}/agreed-plan")
def agree_to_plan_as_the_customer(
    sale_id: SaleIdPath,
    agreed_plan_request: Annotated[MockAgreedPlanRequest, Body()],
    current_merchant: CurrentMerchant,
    mock_customer_simulator_service: MockCustomerSimulatorServiceDependency,
) -> SaleSummaryResponse:
    """Agrees the offer on the shop's CHOOSING sale, as Layer 3 consent will; gives the sale."""
    return SaleSummaryResponse.from_counter_sale(
        mock_customer_simulator_service.agree_to_plan(
            current_merchant, sale_id, agreed_plan_request.offer_id
        )
    )


@mock_customer_simulator_router.post("/payments/{orderId}/completed", status_code=202)
def complete_payment_as_the_customer(
    order_id: Annotated[
        str,
        Path(
            alias="orderId",
            min_length=1,
            max_length=MAXIMUM_IDENTIFIER_LENGTH,
            pattern=VISIBLE_ASCII_PATTERN,
        ),
    ],
    current_merchant: CurrentMerchant,
    mock_customer_simulator_service: MockCustomerSimulatorServiceDependency,
) -> Response:
    """Pays the shop's Mock link; the Mock's signed report then moves the sale (202, no body)."""
    mock_customer_simulator_service.complete_payment(current_merchant, order_id)
    return Response(status_code=202)
