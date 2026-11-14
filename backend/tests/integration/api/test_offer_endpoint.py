"""GET /api/v1/offers on the real application with the Mock gateway."""

import pytest

from tests.integration.api.api_harness import SAMPLE_ITEM_QUERY, ApiHarness

pytestmark = pytest.mark.integration


def test_get_offers_at_sample_price_returns_the_three_design_plans_in_exact_paise(
    mock_api: ApiHarness,
) -> None:
    """Plans A, B and C on ₹22,000 come back in gateway order with exact paise figures."""
    response = mock_api.client.get("/api/v1/offers", params=SAMPLE_ITEM_QUERY)
    assert response.status_code == 200
    assert response.json() == {
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
            {
                "offerId": "mock-offer-cardless-12m",
                "lenderLabel": "Demo cardless lender (Mock)",
                "emiType": "STANDARD",
                "tenureInMonths": 12,
                "monthlyInstallmentInPaise": 205_000,
                "lastInstallmentInPaise": 205_000,
                "extraInTotalInPaise": 260_000,
                "totalPayableInPaise": 2_460_000,
                "priceInPaise": 2_200_000,
            },
        ]
    }


@pytest.mark.parametrize(
    ("query_override", "invalid_field"),
    [
        ({"priceInPaise": 0}, "priceInPaise"),
        ({"priceInPaise": 9_007_199_254_740_992}, "priceInPaise"),
        ({"priceInPaise": "12.5"}, "priceInPaise"),
        ({"productId": ""}, "productId"),
        ({"brandId": "has space"}, "brandId"),
        ({"unexpectedParameter": "x"}, "unexpectedParameter"),
    ],
)
def test_get_offers_with_invalid_query_returns_422_problem_naming_the_field(
    mock_api: ApiHarness, query_override: dict[str, object], invalid_field: str
) -> None:
    """Bad money, ids or unknown parameters are refused before the gateway is asked."""
    response = mock_api.client.get("/api/v1/offers", params={**SAMPLE_ITEM_QUERY, **query_override})
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    problem = response.json()
    assert problem["code"] == "REQUEST_VALIDATION_FAILED"
    assert [field_error["field"] for field_error in problem["fieldErrors"]] == [invalid_field]


def test_get_offers_without_price_returns_422_problem(mock_api: ApiHarness) -> None:
    """A missing required parameter is named in fieldErrors."""
    query_without_price = {
        name: value for name, value in SAMPLE_ITEM_QUERY.items() if name != "priceInPaise"
    }
    response = mock_api.client.get("/api/v1/offers", params=query_without_price)
    assert response.status_code == 422
    assert response.json()["fieldErrors"] == [
        {"field": "priceInPaise", "message": "Field required"}
    ]


def test_get_offers_at_a_price_the_gateway_refuses_returns_502_problem(
    mock_api: ApiHarness,
) -> None:
    """A gateway refusal is surfaced as 502 with the stable rejection code."""
    response = mock_api.client.get(
        "/api/v1/offers", params={**SAMPLE_ITEM_QUERY, "priceInPaise": 1}
    )
    assert response.status_code == 502
    assert response.json()["code"] == "PAYMENT_GATEWAY_REQUEST_REJECTED"
