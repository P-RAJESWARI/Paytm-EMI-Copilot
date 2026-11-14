"""The PaymentGatewayPort contract: behaviour every gateway implementation shows the same way."""

import dataclasses
import re
from urllib.parse import urlsplit

import pytest

from emi_copilot.domain.errors import WebhookSignatureInvalidError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    EmiOffer,
    EmiType,
    GatewayPaymentStatus,
    PaymentStatusResult,
)
from tests.contract.payment_gateway.gateway_contract_harness import GatewayContractHarness
from tests.payment_builders import build_offer_discovery_query, build_payment_link_request

NO_AMOUNT = Money.from_paise(0)
CARD_LIKE_WORDS = frozenset({"card", "pan", "cvv", "cvc", "expiry", "bin"})
WORD_SEPARATOR = re.compile(r"_")
SAMPLE_TRANSACTION_ID = "transaction-sample-0001"


def find_card_like_attribute_names(returned_object: object) -> list[str]:
    """Lists the dataclass field names of an object that contain a card-related word."""
    return [
        field.name
        for field in dataclasses.fields(returned_object)  # type: ignore[arg-type]
        if CARD_LIKE_WORDS & set(WORD_SEPARATOR.split(field.name.lower()))
    ]


def test_gateway_adapter_name_is_short_lowercase_text(
    gateway_contract_harness: GatewayContractHarness,
) -> None:
    """Every gateway names itself for the startup log and the stored gateway mode."""
    assert re.fullmatch(r"[a-z]+", gateway_contract_harness.gateway.adapter_name)


def test_gateway_discover_offers_for_sample_query_returns_valid_offers(
    gateway_contract_harness: GatewayContractHarness,
) -> None:
    """The sample ₹22,000 item gets at least one offer, each a valid EmiOffer with a unique id."""
    offers = gateway_contract_harness.gateway.discover_offers(build_offer_discovery_query())
    assert len(offers) >= 1
    assert all(isinstance(offer, EmiOffer) for offer in offers)
    assert len({offer.offer_id for offer in offers}) == len(offers)


def test_gateway_discover_offers_quotes_are_structurally_sound(
    gateway_contract_harness: GatewayContractHarness,
) -> None:
    """Positive whole-paise installments, a non-negative whole-paise extra and a valid tenure.

    The ₹1 quote-versus-schedule check is the service's job, not the contract's (ADR 0011
    decision 4), so real cashback plans whose quote differs stay valid gateway answers.
    """
    for offer in gateway_contract_harness.gateway.discover_offers(build_offer_discovery_query()):
        assert offer.quoted_monthly_installment > NO_AMOUNT, offer.offer_id
        assert offer.quoted_monthly_installment.is_whole_paise, offer.offer_id
        assert offer.quoted_extra_in_total >= NO_AMOUNT, offer.offer_id
        assert offer.quoted_extra_in_total.is_whole_paise, offer.offer_id
        assert type(offer.tenure_in_months) is int, offer.offer_id
        assert offer.tenure_in_months >= 1, offer.offer_id
        if offer.emi_type is EmiType.NO_COST:
            assert offer.quoted_extra_in_total.is_zero, offer.offer_id


def test_gateway_create_payment_link_returns_https_link_for_the_same_order(
    gateway_contract_harness: GatewayContractHarness,
) -> None:
    """The link is for the order we asked about and opens over https."""
    request = build_payment_link_request()
    payment_link = gateway_contract_harness.gateway.create_payment_link(request)
    assert payment_link.order_id == request.order_id
    assert payment_link.gateway_link_id
    assert urlsplit(payment_link.payment_url).scheme == "https"


def test_gateway_get_payment_status_of_unknown_order_is_not_found(
    gateway_contract_harness: GatewayContractHarness,
) -> None:
    """An order the gateway never saw is a NOT_FOUND result, not an error."""
    status_result = gateway_contract_harness.gateway.get_payment_status("ORDER-NEVER-LINKED")
    assert status_result == PaymentStatusResult(
        order_id="ORDER-NEVER-LINKED",
        status=GatewayPaymentStatus.NOT_FOUND,
        gateway_transaction_id=None,
        amount_paid=None,
    )


def test_gateway_get_payment_status_after_link_creation_is_pending_then_paid(
    gateway_contract_harness: GatewayContractHarness,
) -> None:
    """A fresh link is pending; once the customer pays, the link's amount is reported paid."""
    request = build_payment_link_request()
    gateway = gateway_contract_harness.gateway
    gateway.create_payment_link(request)
    assert gateway.get_payment_status(request.order_id).status is GatewayPaymentStatus.PENDING
    gateway_contract_harness.make_order_paid(request.order_id)
    paid_result = gateway.get_payment_status(request.order_id)
    assert paid_result.order_id == request.order_id
    assert paid_result.status is GatewayPaymentStatus.PAID
    assert paid_result.gateway_transaction_id
    assert paid_result.amount_paid == request.amount


@pytest.mark.parametrize(
    ("status", "amount"),
    [
        (GatewayPaymentStatus.PAID, Money.from_rupees("22000")),
        (GatewayPaymentStatus.FAILED, None),
    ],
    ids=["paid", "failed"],
)
def test_gateway_verify_webhook_turns_a_genuine_notification_into_its_event(
    gateway_contract_harness: GatewayContractHarness,
    status: GatewayPaymentStatus,
    amount: Money | None,
) -> None:
    """A genuinely signed notification becomes the event it describes, field for field."""
    notification = gateway_contract_harness.make_valid_notification(
        "ORDER-SAMPLE-0001", status, SAMPLE_TRANSACTION_ID, amount
    )
    verified_event = gateway_contract_harness.gateway.verify_webhook(notification)
    assert verified_event.order_id == "ORDER-SAMPLE-0001"
    assert verified_event.status is status
    assert verified_event.gateway_transaction_id == SAMPLE_TRANSACTION_ID
    assert verified_event.amount_paid == amount


def test_gateway_verify_webhook_rejects_a_notification_changed_after_signing(
    gateway_contract_harness: GatewayContractHarness,
) -> None:
    """Changing any signed field after signing makes the signature invalid."""
    notification = gateway_contract_harness.make_tampered_notification(
        "ORDER-SAMPLE-0001",
        GatewayPaymentStatus.PAID,
        SAMPLE_TRANSACTION_ID,
        Money.from_rupees("22000"),
    )
    with pytest.raises(WebhookSignatureInvalidError):
        gateway_contract_harness.gateway.verify_webhook(notification)


def test_gateway_verify_webhook_of_a_repeated_notification_gives_equal_events(
    gateway_contract_harness: GatewayContractHarness,
) -> None:
    """Verification has no side effects, so a redelivered webhook reads as the same event."""
    notification = gateway_contract_harness.make_valid_notification(
        "ORDER-SAMPLE-0001",
        GatewayPaymentStatus.PAID,
        SAMPLE_TRANSACTION_ID,
        Money.from_rupees("22000"),
    )
    gateway = gateway_contract_harness.gateway
    assert gateway.verify_webhook(notification) == gateway.verify_webhook(notification)


def test_gateway_returned_objects_expose_no_card_like_attributes(
    gateway_contract_harness: GatewayContractHarness,
) -> None:
    """No offer, link, status or event carries a card number, expiry, CVV or BIN field."""
    gateway = gateway_contract_harness.gateway
    request = build_payment_link_request()
    returned_objects: list[object] = [
        *gateway.discover_offers(build_offer_discovery_query()),
        gateway.create_payment_link(request),
        gateway.get_payment_status(request.order_id),
        gateway.verify_webhook(
            gateway_contract_harness.make_valid_notification(
                request.order_id,
                GatewayPaymentStatus.PAID,
                SAMPLE_TRANSACTION_ID,
                request.amount,
            )
        ),
    ]
    for returned_object in returned_objects:
        assert find_card_like_attribute_names(returned_object) == []


def test_find_card_like_attribute_names_detects_card_fields() -> None:
    """The card-attribute scan itself finds card words as whole name parts only."""

    @dataclasses.dataclass
    class CardLikeSample:
        """A sample object with card-like and harmless field names."""

        card_number: str
        expiry_month: str
        combined_total: str

    assert find_card_like_attribute_names(CardLikeSample("x", "y", "z")) == [
        "card_number",
        "expiry_month",
    ]
