"""Tests for OfferDiscoveryService: priced offers in gateway order, mismatches audited."""

from dataclasses import replace

import pytest

from emi_copilot.domain.errors import PaymentGatewayTimeoutError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import AuditEventType
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from tests.payment_builders import build_offer_discovery_query
from tests.unit.services.conftest import ServiceTestKit


def _build_service(kit: ServiceTestKit) -> OfferDiscoveryService:
    """Wires the service on the kit's fakes."""
    return OfferDiscoveryService(
        kit.payment_gateway, kit.unit_of_work_factory, kit.clock, kit.event_bus
    )


def test_discover_offers_prices_every_offer_in_gateway_order_without_writing(
    kit: ServiceTestKit,
) -> None:
    """Plans A and B come back as quoted, with exact schedules, and nothing is written."""
    priced_offers = _build_service(kit).discover_offers(build_offer_discovery_query())
    assert [offer.offer.offer_id for offer in priced_offers] == ["offer-plan-a", "offer-plan-b"]
    assert priced_offers[0].schedule.last_installment == Money.from_rupees("3666.65")
    assert priced_offers[1].schedule.total_payable == Money.from_rupees("23100")
    assert kit.payment_gateway.discover_offers_calls == [build_offer_discovery_query()]
    assert kit.database.commit_count == 0


def test_discover_offers_audits_a_quote_mismatch_and_still_returns_the_offer(
    kit: ServiceTestKit,
) -> None:
    """A lender quote ₹150 off our schedule is audited, shown with the lender's figure, kept."""
    plan_a, plan_b = kit.payment_gateway.offers
    mismatched_plan_b = replace(plan_b, quoted_monthly_installment=Money.from_rupees("4000"))
    kit.payment_gateway.offers = (mismatched_plan_b, plan_a)
    priced_offers = _build_service(kit).discover_offers(build_offer_discovery_query())
    assert [offer.offer for offer in priced_offers] == [mismatched_plan_b, plan_a]
    assert priced_offers[0].quoted_monthly_installment == Money.from_rupees("4000")
    assert kit.audit_event_types() == [AuditEventType.OFFER_QUOTE_MISMATCH]
    mismatch_audit = kit.last_audit_event()
    assert mismatch_audit.subject_id == "offer-plan-b"
    assert dict(mismatch_audit.details) == {
        "tenure_in_months": 6,
        "price_in_paise": 2_200_000,
        "quoted_monthly_installment_in_paise": 400_000,
        "schedule_regular_installment_in_paise": 385_000,
        "quoted_extra_in_total_in_paise": 110_000,
    }


def test_discover_offers_with_no_offers_returns_an_empty_tuple(kit: ServiceTestKit) -> None:
    """No quote means no plan, and still nothing is written."""
    kit.payment_gateway.offers = ()
    assert _build_service(kit).discover_offers(build_offer_discovery_query()) == ()


def test_discover_offers_lets_a_gateway_error_reach_the_caller(kit: ServiceTestKit) -> None:
    """A failed discovery is never turned into a partial or empty list (ADR 0011)."""

    def time_out() -> None:
        """Fails the discovery as a timeout."""
        raise PaymentGatewayTimeoutError("no answer")

    kit.payment_gateway.before_discover_offers = time_out
    with pytest.raises(PaymentGatewayTimeoutError):
        _build_service(kit).discover_offers(build_offer_discovery_query())
