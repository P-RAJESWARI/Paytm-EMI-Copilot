"""GET /api/v1/offers: every EMI offer the gateway quotes for an item, priced in paise."""

from typing import Annotated

from fastapi import APIRouter, Query

from emi_copilot.api.dependencies import OfferDiscoveryServiceDependency
from emi_copilot.api.openapi_documentation import (
    GATEWAY_FAILURE_PROBLEMS,
    GATEWAY_TIMEOUT_PROBLEM,
    REQUEST_VALIDATION_PROBLEM,
    UNAUTHENTICATED_NOTE,
    describe_problem_responses,
)
from emi_copilot.dtos.offer_dtos import OffersQuery, OffersResponse

offer_router = APIRouter(tags=["offers"])

OFFERS_RESPONSE_EXAMPLE = {
    "offers": [
        {
            "offerId": "mock-offer-no-cost-6m",
            "lenderLabel": "Brand",
            "emiType": "NO_COST",
            "tenureInMonths": 6,
            "monthlyInstallmentInPaise": 366_667,
            "lastInstallmentInPaise": 366_665,
            "extraInTotalInPaise": 0,
            "totalPayableInPaise": 2_200_000,
            "priceInPaise": 2_200_000,
        },
        {
            "offerId": "mock-offer-card-6m",
            "lenderLabel": "Your card's bank",
            "emiType": "STANDARD",
            "tenureInMonths": 6,
            "monthlyInstallmentInPaise": 385_000,
            "lastInstallmentInPaise": 385_000,
            "extraInTotalInPaise": 110_000,
            "totalPayableInPaise": 2_310_000,
            "priceInPaise": 2_200_000,
        },
    ]
}


@offer_router.get(
    "/offers",
    summary="List the EMI offers for an item",
    description=(
        "Asks the payment gateway for every EMI plan on one item at one price and returns them "
        "in the gateway's order; no plan is hidden or ranked. monthlyInstallmentInPaise is the "
        "lender's quoted figure; the last installment, extra in total and total payable come "
        "from our exact schedule, which adds up to the paisa (ADR 0001). " + UNAUTHENTICATED_NOTE
    ),
    response_description="The offers, in the gateway's order.",
    responses={
        200: {"content": {"application/json": {"example": OFFERS_RESPONSE_EXAMPLE}}},
        **describe_problem_responses(
            REQUEST_VALIDATION_PROBLEM, *GATEWAY_FAILURE_PROBLEMS, GATEWAY_TIMEOUT_PROBLEM
        ),
    },
)
def list_offers(
    offers_query: Annotated[OffersQuery, Query()],
    offer_discovery_service: OfferDiscoveryServiceDependency,
) -> OffersResponse:
    """Translates the query into a discovery call and the priced offers into paise."""
    priced_offers = offer_discovery_service.discover_offers(offers_query.to_offer_discovery_query())
    return OffersResponse.from_priced_offers(priced_offers)
