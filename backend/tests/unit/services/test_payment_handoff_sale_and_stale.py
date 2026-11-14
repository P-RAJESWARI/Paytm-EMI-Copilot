"""Tests for the hand-off's sale id, its caller intent and the stale in-progress recovery."""

import hashlib
from dataclasses import replace
from datetime import timedelta

import pytest

from emi_copilot.domain.errors import (
    IdempotencyKeyReusedError,
    InvalidPaymentAttemptError,
    PaymentLinkCreationInProgressError,
    PaymentLinkOutcomeUnknownError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    AuditEventType,
    PaymentAttempt,
    PaymentAttemptStatus,
    PricedEmiOffer,
)
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork
from emi_copilot.services.create_link_outcome import STALE_LINK_CREATION_CAUSE_CODE
from emi_copilot.services.payment_handoff_service import PaymentHandoffService
from emi_copilot.services.payment_handoff_types import CreatePaymentLinkCommand
from tests.fakes.fake_unit_of_work import FakeUnitOfWork, FakeUnitOfWorkFactory
from tests.payment_builders import CREATED_AT, build_payment_attempt
from tests.unit.services.conftest import ServiceTestKit

IDEMPOTENCY_KEY = "idempotency-key-sample-0001"
SALE_ID = "01JCSALE000000000000000001"
LINK_CREATION_STALE_AFTER = timedelta(seconds=26)


class IntentRefusedError(Exception):
    """Stands in for a sale hand-off refusing the link, for example a changed plan."""


class RecordingIntent:
    """A caller intent that records what it was shown and can refuse at either moment."""

    def __init__(self, *, refuses_quote: bool = False, refuses_intent: bool = False) -> None:
        """Sets which of the two moments refuse the hand-off."""
        self.quoted_offers: list[PricedEmiOffer | None] = []
        self.recorded_attempt_ids: list[str] = []
        self._refuses_quote = refuses_quote
        self._refuses_intent = refuses_intent

    def check_quoted_offer(self, priced_offer: PricedEmiOffer | None) -> None:
        """Records the fresh quote and refuses it when told to."""
        self.quoted_offers.append(priced_offer)
        if self._refuses_quote:
            raise IntentRefusedError

    def record_intent(self, unit_of_work: UnitOfWork, new_attempt: PaymentAttempt) -> None:
        """Records the attempt, checks it is not stored yet, and refuses when told to."""
        self.recorded_attempt_ids.append(new_attempt.id)
        assert unit_of_work.payment_attempts.find_by_order_id(new_attempt.order_id) is None
        if self._refuses_intent:
            raise IntentRefusedError


def _build_command(**overrides: object) -> CreatePaymentLinkCommand:
    """Asks for plan B on the ₹22,000 sample item under the sample key."""
    command = CreatePaymentLinkCommand(
        idempotency_key=IDEMPOTENCY_KEY,
        offer_id="offer-plan-b",
        price=Money.from_rupees("22000"),
        product_id="product-sample-0001",
        brand_id="brand-sample-0001",
        category_id="category-sample-0001",
    )
    return replace(command, **overrides)  # type: ignore[arg-type]


def _build_service(
    kit: ServiceTestKit, unit_of_work_factory: FakeUnitOfWorkFactory | None = None
) -> PaymentHandoffService:
    """Wires the service on the kit's fakes with the default 26-second stale limit."""
    return PaymentHandoffService(
        kit.payment_gateway,
        unit_of_work_factory or kit.unit_of_work_factory,
        kit.clock,
        kit.id_generator,
        kit.event_bus,
        link_creation_stale_after=LINK_CREATION_STALE_AFTER,
    )


def test_fingerprint_of_a_sale_less_command_is_the_layer_1_fingerprint() -> None:
    """Adding the optional sale id changed no existing Layer 1 fingerprint."""
    layer_1_canonical_text = (
        '{"brand_id":"brand-sample-0001","category_id":"category-sample-0001",'
        '"offer_id":"offer-plan-b","price_in_paise":2200000,"product_id":"product-sample-0001"}'
    )
    assert (
        _build_command().calculate_request_fingerprint()
        == hashlib.sha256(layer_1_canonical_text.encode("utf-8")).hexdigest()
    )


def test_fingerprint_of_a_sale_command_adds_the_sale_id_in_sorted_order() -> None:
    """The same key on another sale is a different body, so it is caught as key reuse."""
    sale_canonical_text = (
        '{"brand_id":"brand-sample-0001","category_id":"category-sample-0001",'
        '"offer_id":"offer-plan-b","price_in_paise":2200000,"product_id":"product-sample-0001",'
        f'"sale_id":"{SALE_ID}"}}'
    )
    assert (
        _build_command(sale_id=SALE_ID).calculate_request_fingerprint()
        == hashlib.sha256(sale_canonical_text.encode("utf-8")).hexdigest()
    )


@pytest.mark.parametrize("blank_sale_id", ["", "   "])
def test_create_payment_link_command_with_a_blank_sale_id_raises(blank_sale_id: str) -> None:
    """A sale id is either absent or a real id."""
    with pytest.raises(InvalidPaymentAttemptError, match="sale id"):
        _build_command(sale_id=blank_sale_id)


def test_create_payment_link_for_a_sale_stores_the_sale_id_on_the_attempt(
    kit: ServiceTestKit,
) -> None:
    """The attempt remembers the counter sale it pays for."""
    _build_service(kit).create_payment_link(_build_command(sale_id=SALE_ID))
    assert kit.only_attempt().sale_id == SALE_ID


def test_create_payment_link_shows_the_intent_the_fresh_quote_and_the_new_attempt(
    kit: ServiceTestKit,
) -> None:
    """The intent sees the priced plan, then joins the transaction that stores the attempt."""
    intent = RecordingIntent()
    _build_service(kit).create_payment_link(_build_command(), intent)
    (quoted_offer,) = intent.quoted_offers
    assert quoted_offer is not None
    assert quoted_offer.offer.offer_id == "offer-plan-b"
    assert intent.recorded_attempt_ids == [kit.only_attempt().id]


def test_create_payment_link_shows_the_intent_none_for_an_unquoted_offer(
    kit: ServiceTestKit,
) -> None:
    """The intent decides first how a vanished plan is refused."""
    intent = RecordingIntent(refuses_quote=True)
    with pytest.raises(IntentRefusedError):
        _build_service(kit).create_payment_link(_build_command(offer_id="offer-gone"), intent)
    assert intent.quoted_offers == [None]
    assert kit.database.payment_attempts_by_id == {}


def test_create_payment_link_refused_by_the_intent_stores_nothing_and_never_calls_create(
    kit: ServiceTestKit,
) -> None:
    """A refusal inside the intent transaction rolls back the new attempt with it."""
    with pytest.raises(IntentRefusedError):
        _build_service(kit).create_payment_link(
            _build_command(), RecordingIntent(refuses_intent=True)
        )
    assert kit.database.payment_attempts_by_id == {}
    assert kit.payment_gateway.create_link_calls == []


def test_replayed_create_payment_link_never_consults_the_intent(kit: ServiceTestKit) -> None:
    """A replay returns the original result, whatever the sale looks like now."""
    service = _build_service(kit)
    service.create_payment_link(_build_command())
    intent = RecordingIntent(refuses_quote=True, refuses_intent=True)
    assert service.create_payment_link(_build_command(), intent).is_replay is True
    assert (intent.quoted_offers, intent.recorded_attempt_ids) == ([], [])


def _store_in_progress_attempt(kit: ServiceTestKit) -> PaymentAttempt:
    """Stores an attempt left in progress at CREATED_AT by a request that never finished."""
    attempt = build_payment_attempt(
        idempotency_key=IDEMPOTENCY_KEY,
        request_fingerprint=_build_command().calculate_request_fingerprint(),
    )
    kit.store_attempt(attempt)
    return attempt


def test_replay_of_an_attempt_in_progress_for_exactly_the_stale_limit_stores_outcome_unknown(
    kit: ServiceTestKit,
) -> None:
    """At the limit the attempt becomes OUTCOME_UNKNOWN, audited, and nothing is re-sent."""
    attempt = _store_in_progress_attempt(kit)
    kit.clock.advance(LINK_CREATION_STALE_AFTER)
    with pytest.raises(PaymentLinkOutcomeUnknownError):
        _build_service(kit).create_payment_link(_build_command())
    assert kit.only_attempt().status is PaymentAttemptStatus.OUTCOME_UNKNOWN
    assert kit.audit_event_types() == [AuditEventType.PAYMENT_LINK_OUTCOME_UNKNOWN]
    assert kit.last_audit_event().subject_id == attempt.id
    assert kit.last_audit_event().details["cause_error_code"] == STALE_LINK_CREATION_CAUSE_CODE
    assert kit.payment_gateway.create_link_calls == []
    assert kit.payment_gateway.discover_offers_calls == []


def test_replay_of_an_attempt_just_under_the_stale_limit_is_still_in_progress(
    kit: ServiceTestKit,
) -> None:
    """One microsecond before the limit, the first request may still be running."""
    _store_in_progress_attempt(kit)
    kit.clock.advance(LINK_CREATION_STALE_AFTER - timedelta(microseconds=1))
    with pytest.raises(PaymentLinkCreationInProgressError):
        _build_service(kit).create_payment_link(_build_command())
    assert kit.only_attempt().status is PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS
    assert kit.audit_event_types() == []


def test_stale_attempt_replayed_with_a_different_body_is_key_reuse_and_stays_unchanged(
    kit: ServiceTestKit,
) -> None:
    """Only the original body may settle the stale attempt."""
    _store_in_progress_attempt(kit)
    kit.clock.advance(timedelta(hours=1))
    with pytest.raises(IdempotencyKeyReusedError):
        _build_service(kit).create_payment_link(_build_command(offer_id="offer-plan-a"))
    assert kit.only_attempt().status is PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS


class ReportArrivesBeforeTheLockFactory(FakeUnitOfWorkFactory):
    """Moves the attempt to PAID with its link just before the stale check locks the row."""

    def __init__(self, kit: ServiceTestKit, paid_attempt: PaymentAttempt) -> None:
        """Wraps the kit's database; the second unit of work sees the paid attempt."""
        super().__init__(kit.database, kit.clock)
        self._paid_attempt = paid_attempt
        self._opened_count = 0

    def __call__(self) -> FakeUnitOfWork:
        """Stores the gateway report's result when the stale check opens its transaction."""
        self._opened_count += 1
        if self._opened_count == 2:
            self.database.payment_attempts_by_id[self._paid_attempt.id] = self._paid_attempt
        return super().__call__()


def test_stale_attempt_moved_on_by_a_gateway_report_meanwhile_keeps_that_newer_evidence(
    kit: ServiceTestKit,
) -> None:
    """A PAID report found under the lock wins: the stored link is replayed, nothing audited."""
    attempt = _store_in_progress_attempt(kit)
    paid_attempt = replace(
        attempt,
        status=PaymentAttemptStatus.PAID,
        gateway_link_id="link-sample",
        payment_link_url="https://fake-gateway.invalid/pay/sample",
        updated_at=CREATED_AT + timedelta(minutes=1),
    )
    kit.clock.advance(timedelta(minutes=1))
    service = _build_service(kit, ReportArrivesBeforeTheLockFactory(kit, paid_attempt))
    handoff = service.create_payment_link(_build_command())
    assert (handoff.status, handoff.is_replay) == (PaymentAttemptStatus.PAID, True)
    assert kit.only_attempt() == paid_attempt
    assert kit.audit_event_types() == []
