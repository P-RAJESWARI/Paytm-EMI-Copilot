"""MockPaymentGatewayAdapter: labelled, deterministic demo offers, links and payment statuses."""

import logging
from datetime import timedelta

import pytest

from emi_copilot.adapters.payment_gateway.mock_adapter import (
    DEFAULT_PAYMENT_COMPLETION_DELAY,
    MOCK_ACTIVE_WARNING,
    MockPaymentGatewayAdapter,
)
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.domain.errors import (
    InvalidPaymentGatewayValueError,
    PaymentGatewayRejectionReason,
    PaymentGatewayRequestRejectedError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiOffer, EmiType, GatewayPaymentStatus, PaymentLink
from tests.fixed_clock import FixedClock
from tests.payment_builders import (
    CREATED_AT,
    build_offer_discovery_query,
    build_payment_link_request,
)

SYNTHETIC_WEBHOOK_SIGNING_SECRET = bytes(range(32))
SAMPLE_ORDER_ID = "ORDER-SAMPLE-0001"


@pytest.fixture
def fixed_clock() -> FixedClock:
    """Gives a clock that stands still until a test advances it."""
    return FixedClock(CREATED_AT)


@pytest.fixture
def mock_gateway(fixed_clock: FixedClock) -> MockPaymentGatewayAdapter:
    """Gives a fresh Mock with the default 30-second completion delay."""
    return MockPaymentGatewayAdapter(
        clock=fixed_clock, webhook_signing_secret=SYNTHETIC_WEBHOOK_SIGNING_SECRET
    )


def test_mock_adapter_is_a_labelled_payment_gateway_port(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """The Mock implements the port, says "Mock" in its class name and calls itself "mock"."""
    assert isinstance(mock_gateway, PaymentGatewayPort)
    assert "Mock" in type(mock_gateway).__name__
    assert mock_gateway.adapter_name == "mock"


def test_mock_adapter_construction_announces_simulated_payments_as_a_warning(
    fixed_clock: FixedClock, caplog: pytest.LogCaptureFixture
) -> None:
    """Building the Mock logs a WARNING, so nobody can believe real payments are live."""
    with caplog.at_level(logging.WARNING):
        MockPaymentGatewayAdapter(fixed_clock, SYNTHETIC_WEBHOOK_SIGNING_SECRET)
    warning_records = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert [record.getMessage() for record in warning_records] == [MOCK_ACTIVE_WARNING]
    assert "no money moves" in MOCK_ACTIVE_WARNING
    assert "MockPaymentGatewayAdapter" in MOCK_ACTIVE_WARNING


def test_mock_adapter_default_payment_completion_delay_is_thirty_seconds() -> None:
    """Without a configured delay a simulated payment completes 30 seconds after linking."""
    assert timedelta(seconds=30) == DEFAULT_PAYMENT_COMPLETION_DELAY


@pytest.mark.parametrize("secret_length_in_bytes", [0, 1, 31])
def test_mock_adapter_with_short_signing_secret_is_refused(
    fixed_clock: FixedClock, secret_length_in_bytes: int
) -> None:
    """A webhook signing secret shorter than the SHA-256 output (32 bytes) is never accepted."""
    with pytest.raises(ValueError, match="at least 32 bytes"):
        MockPaymentGatewayAdapter(fixed_clock, bytes(secret_length_in_bytes))


def test_mock_adapter_with_negative_completion_delay_is_refused(fixed_clock: FixedClock) -> None:
    """A payment cannot complete before its link was made."""
    with pytest.raises(ValueError, match="cannot be negative"):
        MockPaymentGatewayAdapter(
            fixed_clock, SYNTHETIC_WEBHOOK_SIGNING_SECRET, timedelta(seconds=-1)
        )


def test_mock_adapter_discover_offers_at_sample_price_gives_the_three_design_plans(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """At ₹22,000 the Mock quotes design plans A, B and C exactly, with ADR 0002 labels."""
    assert mock_gateway.discover_offers(build_offer_discovery_query()) == (
        EmiOffer(
            offer_id="mock-offer-no-cost-6m",
            lender_label="Brand",
            emi_type=EmiType.NO_COST,
            tenure_in_months=6,
            quoted_monthly_installment=Money.from_rupees("3666.67"),
            quoted_extra_in_total=Money.from_paise(0),
        ),
        EmiOffer(
            offer_id="mock-offer-card-6m",
            lender_label="Your card's bank",
            emi_type=EmiType.STANDARD,
            tenure_in_months=6,
            quoted_monthly_installment=Money.from_rupees("3850.00"),
            quoted_extra_in_total=Money.from_rupees("1100"),
        ),
        EmiOffer(
            offer_id="mock-offer-cardless-12m",
            lender_label="Demo cardless lender (Mock)",
            emi_type=EmiType.STANDARD,
            tenure_in_months=12,
            quoted_monthly_installment=Money.from_rupees("2050.00"),
            quoted_extra_in_total=Money.from_rupees("2600"),
        ),
    )


@pytest.mark.parametrize(
    ("price_in_rupees", "expected_card_extra_in_rupees", "expected_cardless_extra_in_rupees"),
    [
        ("18000", "900.00", "2127.27"),
        ("1000.10", "50.01", "118.19"),
        ("22000.55", "1100.03", "2600.07"),
    ],
    ids=["other-catalogue-price", "card-extra-exact-half-paisa", "cardless-extra-half-paisa"],
)
def test_mock_adapter_discover_offers_scales_extras_and_rounds_half_up_to_paise(
    mock_gateway: MockPaymentGatewayAdapter,
    price_in_rupees: str,
    expected_card_extra_in_rupees: str,
    expected_cardless_extra_in_rupees: str,
) -> None:
    """Plan B's extra is 5% of the price and C's is price x 2600 / 22000, each rounded half-up."""
    query = build_offer_discovery_query(price=Money.from_rupees(price_in_rupees))
    no_cost_offer, card_offer, cardless_offer = mock_gateway.discover_offers(query)
    assert no_cost_offer.quoted_extra_in_total.is_zero
    assert card_offer.quoted_extra_in_total == Money.from_rupees(expected_card_extra_in_rupees)
    assert cardless_offer.quoted_extra_in_total == Money.from_rupees(
        expected_cardless_extra_in_rupees
    )


def test_mock_adapter_discover_offers_outside_the_demo_catalogue_ignores_the_item_ids(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """Outside the demo catalogue the rule depends on the price only: same plans for any item."""
    other_item_query = build_offer_discovery_query(
        product_id="product-sample-0002", brand_id="brand-sample-0002"
    )
    assert mock_gateway.discover_offers(other_item_query) == mock_gateway.discover_offers(
        build_offer_discovery_query()
    )


@pytest.mark.parametrize(
    "price_in_rupees",
    ["0.01", "0.06", "92233720368547758.07"],
    ids=["installment-rounds-to-zero", "installments-not-representable", "total-overflows-money"],
)
def test_mock_adapter_discover_offers_refuses_a_price_out_of_range_for_emi(
    mock_gateway: MockPaymentGatewayAdapter, price_in_rupees: str
) -> None:
    """A price no plan can be built on is refused as an invalid request, like a real gateway."""
    query = build_offer_discovery_query(price=Money.from_rupees(price_in_rupees))
    with pytest.raises(PaymentGatewayRequestRejectedError) as raised:
        mock_gateway.discover_offers(query)
    assert raised.value.reason is PaymentGatewayRejectionReason.INVALID_REQUEST


def test_mock_adapter_create_payment_link_is_deterministic_per_order_id(
    fixed_clock: FixedClock,
) -> None:
    """The same order id always gets the same link id and URL, on any Mock instance."""
    first_mock_gateway = MockPaymentGatewayAdapter(fixed_clock, SYNTHETIC_WEBHOOK_SIGNING_SECRET)
    second_mock_gateway = MockPaymentGatewayAdapter(fixed_clock, SYNTHETIC_WEBHOOK_SIGNING_SECRET)
    first_link = first_mock_gateway.create_payment_link(build_payment_link_request())
    second_link = second_mock_gateway.create_payment_link(build_payment_link_request())
    assert first_link == second_link
    assert first_link.gateway_link_id.startswith("mock-link-")
    assert first_link == PaymentLink(
        order_id=SAMPLE_ORDER_ID,
        gateway_link_id=first_link.gateway_link_id,
        payment_url=f"https://mock-payments.invalid/pay/{first_link.gateway_link_id}",
    )


def test_mock_adapter_create_payment_link_gives_different_orders_different_links(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """Link ids are derived from the order id, so two orders never share a link."""
    first_link = mock_gateway.create_payment_link(build_payment_link_request())
    second_link = mock_gateway.create_payment_link(
        build_payment_link_request(order_id="ORDER-SAMPLE-0002")
    )
    assert first_link.gateway_link_id != second_link.gateway_link_id


def test_mock_adapter_create_payment_link_twice_for_one_order_is_rejected_as_duplicate(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """A second link for an order id the Mock already holds is refused, as a gateway would."""
    mock_gateway.create_payment_link(build_payment_link_request())
    with pytest.raises(PaymentGatewayRequestRejectedError) as raised:
        mock_gateway.create_payment_link(build_payment_link_request())
    assert raised.value.reason is PaymentGatewayRejectionReason.DUPLICATE_ORDER_ID


def test_mock_adapter_remembers_links_per_instance_only(fixed_clock: FixedClock) -> None:
    """Link state is never global: a second Mock does not know the first one's orders."""
    first_mock_gateway = MockPaymentGatewayAdapter(fixed_clock, SYNTHETIC_WEBHOOK_SIGNING_SECRET)
    second_mock_gateway = MockPaymentGatewayAdapter(fixed_clock, SYNTHETIC_WEBHOOK_SIGNING_SECRET)
    first_mock_gateway.create_payment_link(build_payment_link_request())
    second_mock_status = second_mock_gateway.get_payment_status(SAMPLE_ORDER_ID)
    assert second_mock_status.status is GatewayPaymentStatus.NOT_FOUND


def test_mock_adapter_get_payment_status_is_pending_just_before_the_completion_delay(
    mock_gateway: MockPaymentGatewayAdapter, fixed_clock: FixedClock
) -> None:
    """One microsecond before the delay has passed the payment is still pending."""
    mock_gateway.create_payment_link(build_payment_link_request())
    fixed_clock.advance(DEFAULT_PAYMENT_COMPLETION_DELAY - timedelta(microseconds=1))
    pending_result = mock_gateway.get_payment_status(SAMPLE_ORDER_ID)
    assert pending_result.status is GatewayPaymentStatus.PENDING
    assert pending_result.gateway_transaction_id is None
    assert pending_result.amount_paid is None


def test_mock_adapter_get_payment_status_is_paid_exactly_at_the_completion_delay(
    mock_gateway: MockPaymentGatewayAdapter, fixed_clock: FixedClock
) -> None:
    """Exactly when the delay has passed the link's amount is paid, with a stable transaction id."""
    mock_gateway.create_payment_link(build_payment_link_request())
    fixed_clock.advance(DEFAULT_PAYMENT_COMPLETION_DELAY)
    paid_result = mock_gateway.get_payment_status(SAMPLE_ORDER_ID)
    assert paid_result.status is GatewayPaymentStatus.PAID
    assert paid_result.amount_paid == Money.from_rupees("22000")
    assert paid_result.gateway_transaction_id is not None
    assert paid_result.gateway_transaction_id.startswith("mock-transaction-")
    assert mock_gateway.get_payment_status(SAMPLE_ORDER_ID) == paid_result


def test_mock_adapter_with_configured_delay_completes_after_that_delay(
    fixed_clock: FixedClock,
) -> None:
    """The completion delay is configurable; zero means paid as soon as the link exists."""
    instant_mock_gateway = MockPaymentGatewayAdapter(
        fixed_clock, SYNTHETIC_WEBHOOK_SIGNING_SECRET, payment_completion_delay=timedelta(0)
    )
    instant_mock_gateway.create_payment_link(build_payment_link_request())
    paid_status = instant_mock_gateway.get_payment_status(SAMPLE_ORDER_ID).status
    assert paid_status is GatewayPaymentStatus.PAID


def test_mock_adapter_simulate_payment_outcome_failed_reports_failure_with_transaction(
    mock_gateway: MockPaymentGatewayAdapter, fixed_clock: FixedClock
) -> None:
    """A forced failure wins over the clock and carries a transaction id but no amount paid."""
    mock_gateway.create_payment_link(build_payment_link_request())
    mock_gateway.simulate_payment_outcome(SAMPLE_ORDER_ID, GatewayPaymentStatus.FAILED)
    fixed_clock.advance(DEFAULT_PAYMENT_COMPLETION_DELAY)
    failed_result = mock_gateway.get_payment_status(SAMPLE_ORDER_ID)
    assert failed_result.status is GatewayPaymentStatus.FAILED
    assert failed_result.gateway_transaction_id is not None
    assert failed_result.amount_paid is None


def test_mock_adapter_simulate_payment_outcome_paid_reports_payment_before_the_delay(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """A forced payment is reported straight away, at the link's amount."""
    mock_gateway.create_payment_link(build_payment_link_request())
    mock_gateway.simulate_payment_outcome(SAMPLE_ORDER_ID, GatewayPaymentStatus.PAID)
    paid_result = mock_gateway.get_payment_status(SAMPLE_ORDER_ID)
    assert paid_result.status is GatewayPaymentStatus.PAID
    assert paid_result.amount_paid == Money.from_rupees("22000")


@pytest.mark.parametrize("status", [GatewayPaymentStatus.PENDING, GatewayPaymentStatus.NOT_FOUND])
def test_mock_adapter_simulate_payment_outcome_accepts_only_final_outcomes(
    mock_gateway: MockPaymentGatewayAdapter, status: GatewayPaymentStatus
) -> None:
    """Only PAID or FAILED can be forced; pending and unknown come from the link state itself."""
    mock_gateway.create_payment_link(build_payment_link_request())
    with pytest.raises(InvalidPaymentGatewayValueError, match="PAID or FAILED"):
        mock_gateway.simulate_payment_outcome(SAMPLE_ORDER_ID, status)


def test_mock_adapter_simulate_payment_outcome_for_unknown_order_is_refused(
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """An outcome can only be forced for an order the Mock made a link for."""
    with pytest.raises(InvalidPaymentGatewayValueError, match="no payment link"):
        mock_gateway.simulate_payment_outcome(SAMPLE_ORDER_ID, GatewayPaymentStatus.PAID)
