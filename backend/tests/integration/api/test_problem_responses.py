"""Cross-cutting API behaviour: correlation ids on every answer and the generic 500 problem."""

import pytest

from emi_copilot.api.dependencies import provide_offer_discovery_service
from tests.integration.api.api_harness import SAMPLE_ITEM_QUERY, ApiHarness

pytestmark = pytest.mark.integration

CALLER_CORRELATION_ID = "01JD00000000000000000CALLR"


class ExplodingOfferDiscoveryService:
    """Stands in for any service that fails with an unexpected, untyped exception."""

    def discover_offers(self, _query: object) -> object:
        """Fails the way a programming error would."""
        raise RuntimeError("secret internal detail that must not leak")


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/offers?priceInPaise=2200000&productId=p&brandId=b&categoryId=c"),
        ("GET", "/api/v1/offers"),
        ("GET", "/api/v1/payments/01JD0000000000000000UNKNWN/status"),
        ("POST", "/api/v1/webhooks/paytm"),
        ("GET", "/api/v1/no-such-resource"),
        ("DELETE", "/api/v1/offers"),
    ],
)
def test_every_response_echoes_correlation_id_and_problems_carry_it(
    mock_api: ApiHarness, method: str, path: str
) -> None:
    """Every answer echoes the caller's X-Correlation-Id; problems carry it in the body too."""
    response = mock_api.client.request(
        method, path, headers={"X-Correlation-Id": CALLER_CORRELATION_ID}
    )
    assert response.headers["X-Correlation-Id"] == CALLER_CORRELATION_ID
    if response.status_code >= 400:
        assert response.headers["content-type"] == "application/problem+json"
        assert response.json()["correlationId"] == CALLER_CORRELATION_ID


def test_unknown_route_and_wrong_method_answer_problem_codes(mock_api: ApiHarness) -> None:
    """Framework errors are problems too, with stable codes and the Allow header kept."""
    not_found_response = mock_api.client.get("/api/v1/no-such-resource")
    assert not_found_response.status_code == 404
    assert not_found_response.json()["code"] == "RESOURCE_NOT_FOUND"
    wrong_method_response = mock_api.client.delete("/api/v1/offers")
    assert wrong_method_response.status_code == 405
    assert wrong_method_response.json()["code"] == "METHOD_NOT_ALLOWED"
    assert wrong_method_response.headers["allow"] == "GET"


def test_unexpected_exception_returns_generic_500_problem_with_correlation_id(
    mock_api: ApiHarness,
) -> None:
    """An untyped failure answers a generic problem: no stack trace, no internal text."""
    mock_api.client.app.dependency_overrides[provide_offer_discovery_service] = (  # type: ignore[attr-defined]
        ExplodingOfferDiscoveryService
    )
    response = mock_api.client.get(
        "/api/v1/offers",
        params=SAMPLE_ITEM_QUERY,
        headers={"X-Correlation-Id": CALLER_CORRELATION_ID},
    )
    assert response.status_code == 500
    assert response.headers["X-Correlation-Id"] == CALLER_CORRELATION_ID
    problem = response.json()
    assert problem["code"] == "INTERNAL_SERVER_ERROR"
    assert problem["correlationId"] == CALLER_CORRELATION_ID
    assert "secret internal detail" not in response.text
    assert "Traceback" not in response.text
