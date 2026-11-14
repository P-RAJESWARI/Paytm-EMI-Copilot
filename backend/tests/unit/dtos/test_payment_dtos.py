"""Payment DTOs speak camelCase, keep money in bounded JSON integers and map statuses."""

import json

import pytest
from pydantic import ValidationError

from emi_copilot.domain.payments import PaymentAttemptStatus
from emi_copilot.dtos.payment_link_dtos import CreatePaymentLinkRequest
from emi_copilot.dtos.payment_status_dtos import (
    PUBLIC_STATUS_BY_ATTEMPT_STATUS,
    PaymentStatusResponse,
    PublicPaymentStatus,
)
from emi_copilot.dtos.wire_types import MAXIMUM_SAFE_JAVASCRIPT_INTEGER

VALID_LINK_BODY = {
    "offerId": "offer-plan-b",
    "priceInPaise": 2_200_000,
    "productId": "product-tv-43",
    "brandId": "brand-demo",
    "categoryId": "category-televisions",
}


def test_create_payment_link_request_reads_camel_case_and_builds_the_command() -> None:
    """Wire names are camelCase; the command carries the price as Money and the key."""
    command = CreatePaymentLinkRequest.model_validate(VALID_LINK_BODY).to_command("key-00000001")
    assert command.price.to_paise() == 2_200_000
    assert command.offer_id == "offer-plan-b"
    assert command.idempotency_key == "key-00000001"


@pytest.mark.parametrize(
    "price_in_paise", [0, -1, MAXIMUM_SAFE_JAVASCRIPT_INTEGER + 1, "2200000", 2200000.0, True]
)
def test_create_payment_link_request_refuses_money_outside_bounded_json_integers(
    price_in_paise: object,
) -> None:
    """Zero, negative, unsafe-sized, string, float and boolean amounts are all refused."""
    with pytest.raises(ValidationError):
        CreatePaymentLinkRequest.model_validate_json(
            _to_json({**VALID_LINK_BODY, "priceInPaise": price_in_paise})
        )


def test_create_payment_link_request_accepts_the_largest_safe_amount() -> None:
    """Exactly Number.MAX_SAFE_INTEGER paise is still valid on the wire."""
    body = {**VALID_LINK_BODY, "priceInPaise": MAXIMUM_SAFE_JAVASCRIPT_INTEGER}
    assert CreatePaymentLinkRequest.model_validate_json(_to_json(body)).price_in_paise == (
        MAXIMUM_SAFE_JAVASCRIPT_INTEGER
    )


def test_create_payment_link_request_refuses_unknown_fields() -> None:
    """Unknown fields, card fields included, are never silently accepted."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CreatePaymentLinkRequest.model_validate({**VALID_LINK_BODY, "cardNumber": "4111"})


def test_payment_status_response_serialises_camel_case() -> None:
    """Responses are dumped by alias, so Python names never reach the wire."""
    response = PaymentStatusResponse(
        order_id="order-1", status=PublicPaymentStatus.PAID, amount_paid_in_paise=100
    )
    assert response.model_dump(mode="json", by_alias=True) == {
        "orderId": "order-1",
        "status": "PAID",
        "amountPaidInPaise": 100,
    }


def test_public_status_mapping_covers_every_stored_status_explicitly() -> None:
    """Every stored attempt status has its own public status, so none reaches the wire raw."""
    assert set(PUBLIC_STATUS_BY_ATTEMPT_STATUS) == set(PaymentAttemptStatus)
    assert PUBLIC_STATUS_BY_ATTEMPT_STATUS[PaymentAttemptStatus.LINK_CREATED] is (
        PublicPaymentStatus.AWAITING_PAYMENT
    )


def _to_json(body: dict[str, object]) -> str:
    """Encodes a body as JSON text, as a client would send it."""
    return json.dumps(body)
