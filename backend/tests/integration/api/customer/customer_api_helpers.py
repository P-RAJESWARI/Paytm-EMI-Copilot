"""Drives the customer API over HTTP: the merchant starts a sale, the customer opens its QR."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi.testclient import TestClient

from emi_copilot.domain.merchants import UNLOCKED_PIN_ATTEMPT_STATE, Merchant
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.integration.api.api_harness import ApiHarness
from tests.integration.api.merchant_api_helpers import (
    PIN_HASHER,
    SYNTHETIC_PIN,
    StoredShop,
    pair_and_get_bearer_headers,
    store_demo_catalogue,
)
from tests.integration.api.sale_api_helpers import SALES_PATH

DESIGN_MOMENT = datetime(2026, 11, 15, 9, 30, tzinfo=UTC)
"""The documented examples' moment: 15:00 in Chennai, so references read EMI-1511-NNNN."""
RAVI_MERCHANT_ID = "01JCMERCHANTRAVI0000000001"
RAVI_SHOP_CODE = "RAVI-0193"
RAVI_PRODUCT_PREFIX = "01JCPRODUCTRAVI000000000"
PHONE_128_GB_ID = f"{RAVI_PRODUCT_PREFIX}00"
PHONE_64_GB_ID = f"{RAVI_PRODUCT_PREFIX}01"
CUSTOMER_SESSIONS_PATH = "/api/v1/customer-sessions"
SESSION_TOKEN_HEADER = "X-Customer-Session-Token"  # noqa: S105 - a header name
MOCK_OTP_CODE = "123456"
WRONG_OTP_CODE = "654321"
NO_COST_OFFER_ID = "mock-offer-no-cost-6m"
CARD_OFFER_ID = "mock-offer-card-6m"
CARDLESS_OFFER_ID = "mock-offer-cardless-12m"
PLAN_A_SHOWN_FIGURES = {
    "shownMonthlyInstallmentInPaise": 366_667,
    "shownTotalPayableInPaise": 2_200_000,
}


def as_response(value: Any) -> httpx.Response:  # noqa: ANN401 - TestClient's methods are untyped
    """Narrows a test client's answer to the httpx response it always is."""
    assert isinstance(value, httpx.Response)
    return value


def store_ravi_electronics(harness: ApiHarness) -> dict[str, str]:
    """Commits the design shop with its three M2 products, pairs it and gives its bearer header."""
    hashed_pin = PIN_HASHER.hash_new_pin(SYNTHETIC_PIN)
    with SqlAlchemyUnitOfWork(harness.session_factory, harness.clock) as unit_of_work:
        unit_of_work.merchants.add(
            Merchant(
                id=RAVI_MERCHANT_ID,
                shop_code=RAVI_SHOP_CODE,
                display_name="Ravi Electronics",
                counter_device_label="Counter tablet 1",
                pin_hash_hex=hashed_pin.hash_hex,
                pin_salt_hex=hashed_pin.salt_hex,
                pin_attempt_state=UNLOCKED_PIN_ATTEMPT_STATE,
            )
        )
    store_demo_catalogue(harness, RAVI_MERCHANT_ID, RAVI_PRODUCT_PREFIX)
    return pair_and_get_bearer_headers(
        harness, StoredShop(RAVI_MERCHANT_ID, RAVI_SHOP_CODE, SYNTHETIC_PIN)
    )


def read_qr_token(sale_body: dict[str, Any]) -> str:
    """Reads the token from the #t= fragment of the sale's QR link."""
    customer_url: str = sale_body["qr"]["customerUrl"]
    return customer_url.split("#t=", maxsplit=1)[1]


@dataclass
class CustomerSessionClient:
    """One exchanged QR: the session's path and token, with one helper per customer step."""

    client: TestClient
    sale_id: str
    customer_session_id: str
    session_token: str
    started_body: dict[str, Any]

    @property
    def base_path(self) -> str:
        """Gives /api/v1/customer-sessions/{customerSessionId}."""
        return f"{CUSTOMER_SESSIONS_PATH}/{self.customer_session_id}"

    @property
    def headers(self) -> dict[str, str]:
        """Gives the session token header."""
        return {SESSION_TOKEN_HEADER: self.session_token}

    def get_summary(self) -> httpx.Response:
        """Reads the session summary."""
        return as_response(self.client.get(self.base_path, headers=self.headers))

    def confirm_budget(self, budget_in_paise: int = 300_000) -> httpx.Response:
        """Confirms a monthly budget (₹3,000 by default)."""
        return as_response(
            self.client.put(
                self.base_path + "/budget",
                json={"monthlyBudgetInPaise": budget_in_paise, "hasCustomerConfirmed": True},
                headers=self.headers,
            )
        )

    def answer_comfort_check(self, *, has_customer_consented: bool) -> httpx.Response:
        """Allows or skips the comfort check."""
        return as_response(
            self.client.post(
                self.base_path + "/comfort-check",
                json={"hasCustomerConsented": has_customer_consented},
                headers=self.headers,
            )
        )

    def get_plans(self) -> httpx.Response:
        """Lists the plans."""
        return as_response(self.client.get(self.base_path + "/plans", headers=self.headers))

    def find_alternatives(self, offer_id: str = NO_COST_OFFER_ID) -> httpx.Response:
        """Finds the alternatives to a plan."""
        return as_response(
            self.client.post(
                self.base_path + "/alternatives", json={"offerId": offer_id}, headers=self.headers
            )
        )

    def explain(
        self, offer_id: str = NO_COST_OFFER_ID, accept_language: str | None = None
    ) -> httpx.Response:
        """Asks for the plan's explanation, in the language of the header if one is given."""
        headers = dict(self.headers)
        if accept_language is not None:
            headers["Accept-Language"] = accept_language
        return as_response(
            self.client.post(
                self.base_path + "/explanation", json={"offerId": offer_id}, headers=headers
            )
        )

    def request_code(self) -> httpx.Response:
        """Requests the consent one-time code."""
        return as_response(self.client.post(self.base_path + "/consent/otp", headers=self.headers))

    def give_consent(
        self,
        idempotency_key: str | None = "consent-key-0000000001",
        *,
        offer_id: str = NO_COST_OFFER_ID,
        otp: str = MOCK_OTP_CODE,
        shown_figures: dict[str, int] | None = None,
        accept_language: str | None = None,
    ) -> httpx.Response:
        """Gives consent to plan A as shown by default; None leaves the Idempotency-Key out."""
        headers = dict(self.headers)
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if accept_language is not None:
            headers["Accept-Language"] = accept_language
        body = {
            "offerId": offer_id,
            "otp": otp,
            "hasAgreedToPlan": True,
            **(shown_figures or PLAN_A_SHOWN_FIGURES),
        }
        return as_response(
            self.client.post(self.base_path + "/consent", json=body, headers=headers)
        )

    def get_receipt(self) -> httpx.Response:
        """Reads the receipt."""
        return as_response(self.client.get(self.base_path + "/receipt", headers=self.headers))


@dataclass
class CustomerFlowHarness:
    """The running application with the design shop paired, driven as merchant and customer."""

    api: ApiHarness
    merchant_headers: dict[str, str]

    def start_sale(self, product_id: str = PHONE_128_GB_ID) -> dict[str, Any]:
        """Starts a sale on the counter tablet and gives its body, QR link included."""
        response = self.api.client.post(
            SALES_PATH, json={"productId": product_id}, headers=self.merchant_headers
        )
        assert response.status_code == 201, response.text
        body: dict[str, Any] = response.json()
        return body

    def exchange_qr(self, qr_token: str) -> httpx.Response:
        """Trades a QR token for a customer session, as the phone does."""
        return as_response(self.api.client.post(CUSTOMER_SESSIONS_PATH, json={"qrToken": qr_token}))

    def open_customer_session(
        self, sale_body: dict[str, Any] | None = None
    ) -> CustomerSessionClient:
        """Starts a sale (unless given one) and exchanges its QR for a customer session."""
        started_sale = sale_body or self.start_sale()
        response = self.exchange_qr(read_qr_token(started_sale))
        assert response.status_code == 201, response.text
        body = response.json()
        return CustomerSessionClient(
            self.api.client,
            started_sale["saleId"],
            body["customerSessionId"],
            body["sessionToken"],
            body,
        )

    def read_merchant_sale(self, sale_id: str) -> dict[str, Any]:
        """Reads the merchant's view of one sale."""
        response = self.api.client.get(f"{SALES_PATH}/{sale_id}", headers=self.merchant_headers)
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body

    def ready_for_consent(self) -> CustomerSessionClient:
        """Opens a session, confirms ₹3,000 and requests the code."""
        session = self.open_customer_session()
        assert session.confirm_budget().status_code == 200
        assert session.request_code().status_code == 200
        return session
