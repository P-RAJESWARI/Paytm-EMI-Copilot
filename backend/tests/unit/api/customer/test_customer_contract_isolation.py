"""Phase 3A keeps the customer routers out of the main application (ADR 0012)."""

from fastapi.testclient import TestClient

from emi_copilot.api.customer_contract_application import build_customer_contract_application
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.main import create_application

CUSTOMER_SESSION_PATH = "/api/v1/customer-sessions/{customerSessionId}"


def test_main_application_has_no_customer_session_route() -> None:
    """The main app neither documents nor serves /customer-sessions until Phase 3C."""
    application = create_application(ApplicationSettings())
    main_paths = list(application.openapi()["paths"])
    response = TestClient(application).post(
        "/api/v1/customer-sessions", json={"qrToken": "stub-qr-4821"}
    )
    assert "/api/v1/offers" in main_paths
    assert not [path for path in main_paths if "customer-sessions" in path]
    assert response.status_code == 404
    assert response.json()["code"] == "RESOURCE_NOT_FOUND"


def test_contract_application_serves_only_the_customer_routes_under_api_v1() -> None:
    """The contract app documents the seven customer operations and nothing else."""
    paths = build_customer_contract_application().openapi()["paths"]
    assert {path: sorted(path_item) for path, path_item in paths.items()} == {
        "/api/v1/customer-sessions": ["post"],
        CUSTOMER_SESSION_PATH + "/budget": ["put"],
        CUSTOMER_SESSION_PATH + "/comfort-check": ["post"],
        CUSTOMER_SESSION_PATH + "/plans": ["get"],
        CUSTOMER_SESSION_PATH + "/alternatives": ["post"],
        CUSTOMER_SESSION_PATH + "/consent/otp": ["post"],
        CUSTOMER_SESSION_PATH + "/consent": ["post"],
        CUSTOMER_SESSION_PATH + "/receipt": ["get"],
    }
