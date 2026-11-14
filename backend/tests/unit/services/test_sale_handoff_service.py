"""SaleHandoffService: links only for agreed sales, the agreed plan only, the shop's sales only."""

from dataclasses import replace
from datetime import timedelta

import pytest

from emi_copilot.domain.errors import (
    ChosenPlanNoLongerOfferedError,
    IllegalSaleTransitionError,
    PaymentLinkAlreadyActiveError,
    ProductNotFoundError,
    SaleNotFoundError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    AuditEventType,
    EmiOffer,
    EmiType,
    GatewayPaymentStatus,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentLinkFailureCode,
    PaymentStatusResult,
)
from emi_copilot.domain.sales import EdcEmiProgramme, Sale, SaleStatus
from emi_copilot.services.create_link_outcome import STALE_LINK_CREATION_CAUSE_CODE
from emi_copilot.services.payment_handoff_service import PaymentHandoffService
from emi_copilot.services.payment_status_service import PaymentStatusService
from emi_copilot.services.sale_expiry import SaleExpiryStep
from emi_copilot.services.sale_handoff_service import SaleHandoffService
from emi_copilot.services.sale_handoff_views import HandoffPaymentStatus
from tests.merchant_builders import build_catalogue_product
from tests.payment_builders import CREATED_AT, build_payment_attempt
from tests.sale_builders import SALE_ID, build_sale
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.sale_service_wiring import CHOOSING_LIFETIME, OTHER_PRINCIPAL, PRINCIPAL

KEY = "sale-handoff-key-0001"
OTHER_KEY = "sale-handoff-key-0002"
STALE_AFTER = timedelta(seconds=26)


def _build_service(kit: ServiceTestKit) -> SaleHandoffService:
    """Wires the service and both payment services on the kit's fakes."""
    payment_services = (kit.payment_gateway, kit.unit_of_work_factory, kit.clock, kit.id_generator)
    return SaleHandoffService(
        unit_of_work_factory=kit.unit_of_work_factory,
        clock=kit.clock,
        event_bus=kit.event_bus,
        sale_expiry=SaleExpiryStep(kit.event_bus, CHOOSING_LIFETIME),
        payment_handoff_service=PaymentHandoffService(
            *payment_services, kit.event_bus, link_creation_stale_after=STALE_AFTER
        ),
        payment_status_service=PaymentStatusService(*payment_services, kit.event_bus),
        link_creation_stale_after=STALE_AFTER,
    )


def _store_sale(kit: ServiceTestKit, status: SaleStatus) -> Sale:
    """Stores the shop's product and its sale in the given status (agreed on plan A if needed)."""
    product = build_catalogue_product()
    kit.database.products_by_id[product.id] = product
    sale = build_sale(status=status, status_changed_at=CREATED_AT)
    kit.database.sales_by_id[SALE_ID] = sale
    return sale


def _script_status(kit: ServiceTestKit, order_id: str, status: GatewayPaymentStatus) -> None:
    """Makes the fake gateway report a status for the order."""
    is_paid = status is GatewayPaymentStatus.PAID
    kit.payment_gateway.status_results_by_order_id[order_id] = PaymentStatusResult(
        order_id=order_id,
        status=status,
        gateway_transaction_id="transaction-0001",
        amount_paid=Money.from_rupees("22000") if is_paid else None,
    )


def test_create_payment_link_for_a_ready_sale_links_its_agreed_plan_and_the_sale(
    kit: ServiceTestKit,
) -> None:
    """The link is for the agreed offer, the sale price and the sale's catalogue item."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    handoff = _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    (link_request,) = kit.payment_gateway.create_link_calls
    assert link_request.offer.offer_id == "offer-plan-a"
    assert link_request.amount == Money.from_rupees("22000")
    assert link_request.product_id == "product-synthetic-1"
    assert kit.only_attempt().sale_id == SALE_ID
    assert handoff.is_replay is False


def test_create_payment_link_replayed_returns_the_same_link_with_one_gateway_call(
    kit: ServiceTestKit,
) -> None:
    """Same key, same sale: the original link, even after the sale was paid."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    service = _build_service(kit)
    first_handoff = service.create_payment_link(PRINCIPAL, SALE_ID, KEY)
    _script_status(kit, first_handoff.order_id, GatewayPaymentStatus.PAID)
    service.check_payment_status(PRINCIPAL, SALE_ID)
    replayed_handoff = service.create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.PAID
    assert (replayed_handoff.order_id, replayed_handoff.payment_url) == (
        first_handoff.order_id,
        first_handoff.payment_url,
    )
    assert replayed_handoff.is_replay is True
    assert len(kit.payment_gateway.create_link_calls) == 1


def test_create_payment_link_when_the_quote_changed_is_refused_and_stores_nothing(
    kit: ServiceTestKit,
) -> None:
    """A re-quote with another monthly figure is not the plan the customer agreed to."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    kit.payment_gateway.offers = (
        EmiOffer(
            offer_id="offer-plan-a",
            lender_label="Brand",
            emi_type=EmiType.NO_COST,
            tenure_in_months=6,
            quoted_monthly_installment=Money.from_rupees("3700"),
            quoted_extra_in_total=Money.from_paise(0),
        ),
    )
    with pytest.raises(ChosenPlanNoLongerOfferedError):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert kit.database.payment_attempts_by_id == {}
    assert kit.payment_gateway.create_link_calls == []


def test_create_payment_link_when_the_plan_is_no_longer_quoted_is_refused(
    kit: ServiceTestKit,
) -> None:
    """A vanished offer is the same refusal, not a bare offer-not-found."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    kit.payment_gateway.offers = ()
    with pytest.raises(ChosenPlanNoLongerOfferedError):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)


def test_create_payment_link_after_a_payment_not_completed_retries_the_sale_with_the_link(
    kit: ServiceTestKit,
) -> None:
    """PAYMENT_NOT_COMPLETED goes back to READY_TO_PAY in the transaction of the new attempt."""
    _store_sale(kit, SaleStatus.PAYMENT_NOT_COMPLETED)
    kit.clock.advance(timedelta(minutes=5))
    _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    stored_sale = kit.database.sales_by_id[SALE_ID]
    assert stored_sale.status is SaleStatus.READY_TO_PAY
    assert stored_sale.status_changed_at == CREATED_AT + timedelta(minutes=5)
    assert kit.audit_event_types() == [
        AuditEventType.SALE_STATUS_CHANGED,
        AuditEventType.PAYMENT_LINK_CREATED,
    ]
    assert kit.database.audit_events[0].details["payment_attempt_id"] == kit.only_attempt().id
    assert kit.database.funnel_events == []


@pytest.mark.parametrize("status", [SaleStatus.CHOOSING, SaleStatus.EXPIRED])
def test_create_payment_link_before_agreement_is_a_state_conflict(
    kit: ServiceTestKit, status: SaleStatus
) -> None:
    """No agreed plan, no link, and the gateway is never asked."""
    _store_sale(kit, status)
    with pytest.raises(IllegalSaleTransitionError):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert kit.payment_gateway.discover_offers_calls == []


def test_create_payment_link_for_a_paid_sale_with_a_new_key_is_a_state_conflict(
    kit: ServiceTestKit,
) -> None:
    """A paid sale takes no second link."""
    _store_sale(kit, SaleStatus.PAID)
    with pytest.raises(IllegalSaleTransitionError, match="PAID"):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, OTHER_KEY)
    assert kit.payment_gateway.discover_offers_calls == []


def test_create_payment_link_when_the_sale_was_paid_during_the_quote_is_a_state_conflict(
    kit: ServiceTestKit,
) -> None:
    """The status is checked again under the lock, after the quote, before anything is stored."""
    sale = _store_sale(kit, SaleStatus.READY_TO_PAY)
    paid_sale = build_sale(status=SaleStatus.PAID, status_changed_at=CREATED_AT)
    kit.payment_gateway.before_discover_offers = lambda: kit.database.sales_by_id.update(
        {sale.id: paid_sale}
    )
    with pytest.raises(IllegalSaleTransitionError, match="RETRY_PAYMENT"):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert kit.database.payment_attempts_by_id == {}
    assert kit.payment_gateway.create_link_calls == []


def test_create_payment_link_for_a_sale_deleted_during_the_quote_is_not_found(
    kit: ServiceTestKit,
) -> None:
    """The lock finds no sale: not found, and nothing is stored."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    # A lambda, not the bound method: each fake commit replaces the dict, so look it up late.
    kit.payment_gateway.before_discover_offers = lambda: kit.database.sales_by_id.clear()  # noqa: PLW0108
    with pytest.raises(SaleNotFoundError):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert kit.database.payment_attempts_by_id == {}


def test_hand_off_of_another_shops_sale_is_not_found(kit: ServiceTestKit) -> None:
    """Reading, linking and checking another shop's sale all answer not found."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    service = _build_service(kit)
    with pytest.raises(SaleNotFoundError):
        service.get_handoff(OTHER_PRINCIPAL, SALE_ID)
    with pytest.raises(SaleNotFoundError):
        service.create_payment_link(OTHER_PRINCIPAL, SALE_ID, KEY)
    with pytest.raises(SaleNotFoundError):
        service.check_payment_status(OTHER_PRINCIPAL, SALE_ID)


def test_create_payment_link_for_a_sale_whose_product_vanished_raises(kit: ServiceTestKit) -> None:
    """A stored sale always has its product; if not, nothing is guessed."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    kit.database.products_by_id.clear()
    with pytest.raises(ProductNotFoundError):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)


def test_get_handoff_of_a_ready_sale_without_a_link_shows_edc_steps_and_waiting(
    kit: ServiceTestKit,
) -> None:
    """M4 before any link: Brand EMI steps on the price, waiting, no confirmation time."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    view = _build_service(kit).get_handoff(PRINCIPAL, SALE_ID)
    assert view.edc_instructions.emi_programme is EdcEmiProgramme.BRAND_EMI
    assert view.edc_instructions.amount == Money.from_rupees("22000")
    assert view.latest_payment_link is None
    assert view.payment_status is HandoffPaymentStatus.WAITING
    assert view.payment_confirmed_at is None
    assert view.counter_sale.product_name == build_catalogue_product().name


@pytest.mark.parametrize("status", [SaleStatus.CHOOSING, SaleStatus.EXPIRED])
def test_get_handoff_before_agreement_is_a_state_conflict(
    kit: ServiceTestKit, status: SaleStatus
) -> None:
    """There is nothing to hand off while the customer is choosing or after expiry."""
    _store_sale(kit, status)
    with pytest.raises(IllegalSaleTransitionError, match="no agreed plan"):
        _build_service(kit).get_handoff(PRINCIPAL, SALE_ID)


def test_get_handoff_of_an_overdue_choosing_sale_commits_its_expiry_before_refusing(
    kit: ServiceTestKit,
) -> None:
    """The refusal never undoes the expiry it found."""
    _store_sale(kit, SaleStatus.CHOOSING)
    kit.clock.advance(CHOOSING_LIFETIME)
    with pytest.raises(IllegalSaleTransitionError, match="EXPIRED"):
        _build_service(kit).get_handoff(PRINCIPAL, SALE_ID)
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.EXPIRED


def test_check_payment_status_applies_a_paid_report_to_the_attempt_and_the_sale(
    kit: ServiceTestKit,
) -> None:
    """The gateway's server-side answer moves the sale to PAID through the usual events."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    service = _build_service(kit)
    handoff = service.create_payment_link(PRINCIPAL, SALE_ID, KEY)
    _script_status(kit, handoff.order_id, GatewayPaymentStatus.PAID)
    kit.clock.advance(timedelta(minutes=2))
    view = service.check_payment_status(PRINCIPAL, SALE_ID)
    assert view.payment_status is HandoffPaymentStatus.PAID
    assert view.payment_confirmed_at == CREATED_AT + timedelta(minutes=2)
    assert view.latest_payment_link is not None
    assert view.latest_payment_link.status is PaymentAttemptStatus.PAID
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.PAID


def test_check_payment_status_of_a_failed_payment_shows_not_completed(kit: ServiceTestKit) -> None:
    """A failed payment is "not completed", never "declined"."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    service = _build_service(kit)
    handoff = service.create_payment_link(PRINCIPAL, SALE_ID, KEY)
    _script_status(kit, handoff.order_id, GatewayPaymentStatus.FAILED)
    assert (
        service.check_payment_status(PRINCIPAL, SALE_ID).payment_status
        is HandoffPaymentStatus.NOT_COMPLETED
    )


def test_check_payment_status_without_an_attempt_or_once_paid_never_asks_the_gateway(
    kit: ServiceTestKit,
) -> None:
    """No link yet: nothing to ask. Paid: final, so nothing to ask either."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    service = _build_service(kit)
    assert service.check_payment_status(PRINCIPAL, SALE_ID).payment_status is (
        HandoffPaymentStatus.WAITING
    )
    handoff = service.create_payment_link(PRINCIPAL, SALE_ID, KEY)
    _script_status(kit, handoff.order_id, GatewayPaymentStatus.PAID)
    service.check_payment_status(PRINCIPAL, SALE_ID)
    service.check_payment_status(PRINCIPAL, SALE_ID)
    assert kit.payment_gateway.status_check_calls == [handoff.order_id]


ACTIVE_LINK_STATUSES = [
    PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS,
    PaymentAttemptStatus.LINK_CREATED,
    PaymentAttemptStatus.PAYMENT_PENDING,
    PaymentAttemptStatus.OUTCOME_UNKNOWN,
    PaymentAttemptStatus.PAID,
]


def _store_earlier_attempt(kit: ServiceTestKit, status: PaymentAttemptStatus) -> None:
    """Stores an earlier attempt of the sale, under another key, in the given status."""
    failure_code = (
        PaymentLinkFailureCode.GATEWAY_UNAVAILABLE
        if status is PaymentAttemptStatus.LINK_CREATION_FAILED
        else None
    )
    kit.store_attempt(
        build_payment_attempt(
            9, sale_id=SALE_ID, status=status, failure_code=failure_code, idempotency_key=OTHER_KEY
        )
    )


@pytest.mark.parametrize("attempt_status", ACTIVE_LINK_STATUSES)
def test_create_payment_link_with_a_new_key_while_the_latest_link_may_be_paid_is_refused(
    kit: ServiceTestKit, attempt_status: PaymentAttemptStatus
) -> None:
    """A second link could be paid twice: refused, nothing stored and no link asked for."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    _store_earlier_attempt(kit, attempt_status)
    with pytest.raises(PaymentLinkAlreadyActiveError, match=attempt_status.value):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert len(kit.database.payment_attempts_by_id) == 1
    assert kit.payment_gateway.create_link_calls == []
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.READY_TO_PAY


def _store_earlier_attempt_created(
    kit: ServiceTestKit, status: PaymentAttemptStatus, age: timedelta
) -> PaymentAttempt:
    """Stores an earlier attempt of the sale created `age` before now, under another key."""
    earlier_attempt = build_payment_attempt(
        9,
        sale_id=SALE_ID,
        status=status,
        idempotency_key=OTHER_KEY,
        created_at=kit.clock.now() - age,
        updated_at=kit.clock.now() - age,
    )
    kit.store_attempt(earlier_attempt)
    return earlier_attempt


def test_create_payment_link_with_a_new_key_after_a_stale_creation_records_it_unknown_then_links(
    kit: ServiceTestKit,
) -> None:
    """A crash mid-creation: whatever key asks, the stale attempt is stored OUTCOME_UNKNOWN.

    It is audited LINK_CREATION_STALE; the gateway then holds no link for it, so a new one is made.
    """
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    stale_attempt = _store_earlier_attempt_created(
        kit, PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS, STALE_AFTER
    )
    handoff = _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    stored_stale_attempt = kit.database.payment_attempts_by_id[stale_attempt.id]
    assert stored_stale_attempt.status is PaymentAttemptStatus.OUTCOME_UNKNOWN
    assert kit.audit_event_types()[0] is AuditEventType.PAYMENT_LINK_OUTCOME_UNKNOWN
    assert kit.database.audit_events[0].details["cause_error_code"] == (
        STALE_LINK_CREATION_CAUSE_CODE
    )
    assert kit.payment_gateway.status_check_calls == [stale_attempt.order_id]
    assert handoff.order_id != stale_attempt.order_id
    assert len(kit.payment_gateway.create_link_calls) == 1


def test_create_payment_link_with_a_new_key_while_a_creation_is_fresh_is_refused(
    kit: ServiceTestKit,
) -> None:
    """Just under the limit the first create may still be running: refused, gateway not asked."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    _store_earlier_attempt_created(
        kit, PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS, STALE_AFTER - timedelta(seconds=1)
    )
    with pytest.raises(PaymentLinkAlreadyActiveError, match="LINK_CREATION_IN_PROGRESS"):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert kit.payment_gateway.status_check_calls == []
    assert kit.database.audit_events == []


def test_create_payment_link_with_a_new_key_while_an_unknown_outcome_is_young_is_refused(
    kit: ServiceTestKit,
) -> None:
    """A timed-out create younger than the limit is not asked about yet: refused."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    _store_earlier_attempt_created(
        kit, PaymentAttemptStatus.OUTCOME_UNKNOWN, STALE_AFTER - timedelta(seconds=1)
    )
    with pytest.raises(PaymentLinkAlreadyActiveError, match="OUTCOME_UNKNOWN"):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert kit.payment_gateway.status_check_calls == []
    assert kit.payment_gateway.create_link_calls == []


def test_create_payment_link_with_a_new_key_after_an_old_unknown_outcome_not_found_links(
    kit: ServiceTestKit,
) -> None:
    """The gateway holds no link for an old timed-out create: a new link, the old row untouched."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    unknown_attempt = _store_earlier_attempt_created(
        kit, PaymentAttemptStatus.OUTCOME_UNKNOWN, STALE_AFTER
    )
    handoff = _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert kit.database.payment_attempts_by_id[unknown_attempt.id] == unknown_attempt
    assert kit.payment_gateway.status_check_calls == [unknown_attempt.order_id]
    assert handoff.is_replay is False
    assert len(kit.payment_gateway.create_link_calls) == 1
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.READY_TO_PAY


def test_create_payment_link_with_a_new_key_after_an_old_unknown_outcome_pending_is_refused(
    kit: ServiceTestKit,
) -> None:
    """The old create did make a link: the PENDING report is applied and no second link made."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    unknown_attempt = _store_earlier_attempt_created(
        kit, PaymentAttemptStatus.OUTCOME_UNKNOWN, STALE_AFTER
    )
    _script_status(kit, unknown_attempt.order_id, GatewayPaymentStatus.PENDING)
    with pytest.raises(PaymentLinkAlreadyActiveError, match="PAYMENT_PENDING"):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    stored_attempt = kit.database.payment_attempts_by_id[unknown_attempt.id]
    assert stored_attempt.status is PaymentAttemptStatus.PAYMENT_PENDING
    assert kit.payment_gateway.create_link_calls == []


def test_create_payment_link_with_a_new_key_after_an_old_unknown_outcome_paid_pays_the_sale(
    kit: ServiceTestKit,
) -> None:
    """The customer paid on the old link: the sale becomes PAID and no new link is made."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    unknown_attempt = _store_earlier_attempt_created(
        kit, PaymentAttemptStatus.OUTCOME_UNKNOWN, STALE_AFTER
    )
    _script_status(kit, unknown_attempt.order_id, GatewayPaymentStatus.PAID)
    with pytest.raises(PaymentLinkAlreadyActiveError, match="PAID"):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert kit.database.payment_attempts_by_id[unknown_attempt.id].status is (
        PaymentAttemptStatus.PAID
    )
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.PAID
    assert kit.payment_gateway.create_link_calls == []


def test_create_payment_link_when_a_report_moves_the_proven_attempt_before_the_lock_is_refused(
    kit: ServiceTestKit,
) -> None:
    """NOT_FOUND counts only while the attempt is still OUTCOME_UNKNOWN under the sale's lock."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    unknown_attempt = _store_earlier_attempt_created(
        kit, PaymentAttemptStatus.OUTCOME_UNKNOWN, STALE_AFTER
    )
    pending_attempt = replace(unknown_attempt, status=PaymentAttemptStatus.PAYMENT_PENDING)
    kit.payment_gateway.before_discover_offers = lambda: kit.store_attempt(pending_attempt)
    with pytest.raises(PaymentLinkAlreadyActiveError, match="PAYMENT_PENDING"):
        _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert kit.payment_gateway.create_link_calls == []


@pytest.mark.parametrize(
    ("attempt_status", "sale_status"),
    [
        (PaymentAttemptStatus.LINK_CREATION_FAILED, SaleStatus.READY_TO_PAY),
        (PaymentAttemptStatus.PAYMENT_FAILED, SaleStatus.PAYMENT_NOT_COMPLETED),
    ],
)
def test_create_payment_link_with_a_new_key_after_a_failed_or_refused_link_makes_a_new_one(
    kit: ServiceTestKit, attempt_status: PaymentAttemptStatus, sale_status: SaleStatus
) -> None:
    """M4 "Try again": nothing can be paid on the old link, so a new key makes a new one."""
    _store_sale(kit, sale_status)
    _store_earlier_attempt(kit, attempt_status)
    handoff = _build_service(kit).create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert handoff.is_replay is False
    assert len(kit.payment_gateway.create_link_calls) == 1
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.READY_TO_PAY


def test_create_payment_link_with_the_known_key_while_its_link_is_active_replays_it(
    kit: ServiceTestKit,
) -> None:
    """The active-link refusal is for new keys only; the original key still replays."""
    _store_sale(kit, SaleStatus.READY_TO_PAY)
    service = _build_service(kit)
    first_handoff = service.create_payment_link(PRINCIPAL, SALE_ID, KEY)
    with pytest.raises(PaymentLinkAlreadyActiveError):
        service.create_payment_link(PRINCIPAL, SALE_ID, OTHER_KEY)
    replayed_handoff = service.create_payment_link(PRINCIPAL, SALE_ID, KEY)
    assert replayed_handoff.order_id == first_handoff.order_id
    assert replayed_handoff.is_replay is True
    assert len(kit.payment_gateway.create_link_calls) == 1
