"""Runs the Phase 3A customer contract application on a fixed clock with sequential ids."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from emi_copilot.api.customer_contract_application import build_customer_contract_application
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock

EXAMPLE_MOMENT = datetime(2026, 11, 15, 9, 30, tzinfo=UTC)
STANDARD_QR_TOKEN = "stub-qr-4821"  # noqa: S105 - published sample QR value
RISKY_QR_TOKEN = "stub-qr-4822"  # noqa: S105 - published sample QR value
SESSION_TOKEN_HEADER = "X-Customer-Session-Token"  # noqa: S105 - a header name
STUB_CODE = "123456"
NO_COST_OFFER_ID = "mock-offer-no-cost-6m"
DESIGN_PLAN_A_SHOWN_FIGURES = {
    "shownMonthlyInstallmentInPaise": 366_667,
    "shownTotalPayableInPaise": 2_200_000,
}


@dataclass
class CustomerSessionClient:
    """One started session: its base URL and token, with helpers for each step."""

    client: TestClient
    customer_session_id: str
    session_token: str
    started_body: dict[str, Any]

    @property
    def base_path(self) -> str:
        """Gives /api/v1/customer-sessions/{customerSessionId}."""
        return f"/api/v1/customer-sessions/{self.customer_session_id}"

    @property
    def headers(self) -> dict[str, str]:
        """Gives the session token header."""
        return {SESSION_TOKEN_HEADER: self.session_token}

    def confirm_budget(self, budget_in_paise: int = 300_000) -> httpx.Response:
        """Confirms a monthly budget."""
        response: httpx.Response = self.client.put(
            self.base_path + "/budget",
            json={"monthlyBudgetInPaise": budget_in_paise, "hasCustomerConfirmed": True},
            headers=self.headers,
        )
        return response

    def run_comfort_check(self, *, has_customer_consented: bool) -> httpx.Response:
        """Allows or skips the comfort check."""
        response: httpx.Response = self.client.post(
            self.base_path + "/comfort-check",
            json={"hasCustomerConsented": has_customer_consented},
            headers=self.headers,
        )
        return response

    def get_plans(self) -> httpx.Response:
        """Lists the plans."""
        response: httpx.Response = self.client.get(self.base_path + "/plans", headers=self.headers)
        return response

    def find_alternatives(self, offer_id: str = NO_COST_OFFER_ID) -> httpx.Response:
        """Finds alternatives to a plan."""
        response: httpx.Response = self.client.post(
            self.base_path + "/alternatives", json={"offerId": offer_id}, headers=self.headers
        )
        return response

    def request_code(self) -> httpx.Response:
        """Requests the one-time code."""
        response: httpx.Response = self.client.post(
            self.base_path + "/consent/otp", headers=self.headers
        )
        return response

    def give_consent(
        self,
        idempotency_key: str | None = "stub-consent-key-0001",
        *,
        offer_id: str = NO_COST_OFFER_ID,
        otp: str = STUB_CODE,
        selection: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Gives consent; None leaves the Idempotency-Key header out.

        selection replaces the shown no-cost 6-month figures on the 128 GB phone, for example
        with a downPaymentInPaise or a productId and their own shown figures.
        """
        headers = dict(self.headers)
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        body = {
            "offerId": offer_id,
            "otp": otp,
            "hasAgreedToPlan": True,
            **(selection or DESIGN_PLAN_A_SHOWN_FIGURES),
        }
        response: httpx.Response = self.client.post(
            self.base_path + "/consent", json=body, headers=headers
        )
        return response

    def get_receipt(self) -> httpx.Response:
        """Gets the receipt."""
        response: httpx.Response = self.client.get(
            self.base_path + "/receipt", headers=self.headers
        )
        return response


@dataclass
class CustomerApi:
    """The test client of the contract application and its fixed clock."""

    client: TestClient
    clock: FixedClock

    def start_session(self, qr_token: str = STANDARD_QR_TOKEN) -> CustomerSessionClient:
        """Scans a sample QR and gives a client for the session."""
        response = self.client.post("/api/v1/customer-sessions", json={"qrToken": qr_token})
        assert response.status_code == 201, response.text
        body = response.json()
        return CustomerSessionClient(
            self.client, body["customerSessionId"], body["sessionToken"], body
        )


@pytest.fixture
def customer_api() -> CustomerApi:
    """Builds a fresh contract application, so no test sees another's sessions."""
    clock = FixedClock(EXAMPLE_MOMENT)
    application = build_customer_contract_application(
        clock=clock, id_generator=SequentialIdGenerator()
    )
    return CustomerApi(client=TestClient(application), clock=clock)
