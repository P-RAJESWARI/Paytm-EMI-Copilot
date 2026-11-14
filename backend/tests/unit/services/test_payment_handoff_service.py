"""Tests for PaymentHandoffService: one gateway call per key, every outcome stored and replayed."""

from dataclasses import replace

import pytest

from emi_copilot.domain.errors import (
    DomainError,
    IdempotencyKeyReusedError,
    InvalidPaymentGatewayValueError,
    OfferNotFoundError,
    PaymentAttemptAlreadyExistsError,
    PaymentGatewayRejectionReason,
    PaymentGatewayRequestRejectedError,
    PaymentGatewayTimeoutError,
    PaymentGatewayUnavailableError,
    PaymentLinkCreationFailedError,
    PaymentLinkCreationInProgressError,
    PaymentLinkFailureCode,
    PaymentLinkOutcomeUnknownError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import AuditEventType, PaymentAttemptStatus
from emi_copilot.services.payment_handoff_service import PaymentHandoffService
from emi_copilot.services.payment_handoff_types import CreatePaymentLinkCommand
from tests.payment_builders import build_payment_attempt, build_standard_offer_snapshot
from tests.unit.services.conftest import ServiceTestKit

IDEMPOTENCY_KEY = "idempotency-key-sample-0001"
# The kit's ids, in the order the service asks for them.
EXPECTED_ORDER_ID = "01JCTESTID0000000000000001"
EXPECTED_CUSTOMER_REFERENCE = "01JCTESTID0000000000000002"
EXPECTED_ATTEMPT_ID = "01JCTESTID0000000000000003"


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


def _build_service(kit: ServiceTestKit) -> PaymentHandoffService:
    """Wires the service on the kit's fakes."""
    return PaymentHandoffService(
        kit.payment_gateway, kit.unit_of_work_factory, kit.clock, kit.id_generator, kit.event_bus
    )


def _create_expecting(
    kit: ServiceTestKit, error_type: type[DomainError], command: CreatePaymentLinkCommand
) -> DomainError:
    """Runs create_payment_link, which must raise error_type, and returns the error."""
    with pytest.raises(error_type) as raised:
        _build_service(kit).create_payment_link(command)
    return raised.value


def test_create_payment_link_stores_link_created_and_audits_it(kit: ServiceTestKit) -> None:
    """A new key: one gateway call, the attempt is LINK_CREATED and PAYMENT_LINK_CREATED audited."""
    handoff = _build_service(kit).create_payment_link(_build_command())
    stored_attempt = kit.only_attempt()
    assert handoff.is_replay is False
    assert handoff.order_id == EXPECTED_ORDER_ID
    assert handoff.payment_url == f"https://fake-gateway.invalid/pay/{EXPECTED_ORDER_ID}"
    assert handoff.status is PaymentAttemptStatus.LINK_CREATED
    assert stored_attempt.id == EXPECTED_ATTEMPT_ID
    assert stored_attempt.status is PaymentAttemptStatus.LINK_CREATED
    assert stored_attempt.gateway_mode == "fake"
    assert stored_attempt.payment_link_url == handoff.payment_url
    assert kit.audit_event_types() == [AuditEventType.PAYMENT_LINK_CREATED]
    assert kit.last_audit_event().subject_id == EXPECTED_ATTEMPT_ID
    assert len(kit.payment_gateway.create_link_calls) == 1


def test_create_payment_link_takes_every_figure_from_a_fresh_gateway_quote(
    kit: ServiceTestKit,
) -> None:
    """The client names the offer only; amounts and plan come from the server-side quote."""
    _build_service(kit).create_payment_link(_build_command())
    (link_request,) = kit.payment_gateway.create_link_calls
    assert link_request.offer == build_standard_offer_snapshot()
    assert link_request.amount == Money.from_rupees("22000")
    assert link_request.customer_reference == EXPECTED_CUSTOMER_REFERENCE
    assert kit.payment_gateway.discover_offers_calls == [
        _build_command().to_offer_discovery_query()
    ]


def test_create_payment_link_commits_the_attempt_in_progress_before_calling_the_gateway(
    kit: ServiceTestKit,
) -> None:
    """The in-progress row is already committed when the gateway is called."""
    statuses_seen_by_the_gateway: list[PaymentAttemptStatus] = []
    kit.payment_gateway.before_create_link = lambda: statuses_seen_by_the_gateway.append(
        kit.only_attempt().status
    )
    _build_service(kit).create_payment_link(_build_command())
    assert statuses_seen_by_the_gateway == [PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS]


def test_create_payment_link_replayed_with_the_same_body_returns_the_stored_link(
    kit: ServiceTestKit,
) -> None:
    """Same key and body: the stored result, no second discovery or gateway call, no new row."""
    service = _build_service(kit)
    first_handoff = service.create_payment_link(_build_command())
    replayed_handoff = service.create_payment_link(_build_command())
    assert replayed_handoff == replace(first_handoff, is_replay=True)
    assert len(kit.payment_gateway.create_link_calls) == 1
    assert len(kit.payment_gateway.discover_offers_calls) == 1
    assert len(kit.database.audit_events) == 1


@pytest.mark.parametrize(
    "changed_field",
    [
        {"offer_id": "offer-plan-a"},
        {"price": Money.from_rupees("22000.01")},
        {"product_id": "product-sample-0002"},
        {"brand_id": "brand-sample-0002"},
        {"category_id": "category-sample-0002"},
    ],
)
def test_create_payment_link_replayed_with_a_different_body_raises_key_reused(
    kit: ServiceTestKit, changed_field: dict[str, object]
) -> None:
    """Same key, any different field: IDEMPOTENCY_KEY_REUSED and no further gateway call."""
    service = _build_service(kit)
    service.create_payment_link(_build_command())
    _create_expecting(kit, IdempotencyKeyReusedError, _build_command(**changed_field))
    assert len(kit.payment_gateway.create_link_calls) == 1


@pytest.mark.parametrize(
    "unknown_outcome_error",
    [
        PaymentGatewayTimeoutError("no answer"),
        InvalidPaymentGatewayValueError("unreadable reply"),
    ],
)
def test_create_payment_link_with_an_unknown_outcome_stores_it_and_never_resends(
    kit: ServiceTestKit, unknown_outcome_error: DomainError
) -> None:
    """A timeout or unreadable reply is OUTCOME_UNKNOWN; a replay raises and never resends."""
    kit.payment_gateway.create_link_error = unknown_outcome_error
    raised_error = _create_expecting(kit, type(unknown_outcome_error), _build_command())
    assert raised_error is unknown_outcome_error
    assert kit.only_attempt().status is PaymentAttemptStatus.OUTCOME_UNKNOWN
    assert kit.audit_event_types() == [AuditEventType.PAYMENT_LINK_OUTCOME_UNKNOWN]
    assert kit.last_audit_event().details["cause_error_code"] == unknown_outcome_error.code
    kit.payment_gateway.create_link_error = None
    _create_expecting(kit, PaymentLinkOutcomeUnknownError, _build_command())
    assert len(kit.payment_gateway.create_link_calls) == 1


@pytest.mark.parametrize(
    ("failure", "expected_failure_code"),
    [
        (PaymentGatewayUnavailableError("not sent"), PaymentLinkFailureCode.GATEWAY_UNAVAILABLE),
        (
            PaymentGatewayRequestRejectedError(
                PaymentGatewayRejectionReason.GATEWAY_INTERNAL_ERROR, "failed on its side"
            ),
            PaymentLinkFailureCode.GATEWAY_INTERNAL_ERROR,
        ),
    ],
)
def test_create_payment_link_that_certainly_failed_stores_and_replays_its_code(
    kit: ServiceTestKit, failure: DomainError, expected_failure_code: PaymentLinkFailureCode
) -> None:
    """Unavailable or refused: LINK_CREATION_FAILED with its code; a replay raises that code."""
    kit.payment_gateway.create_link_error = failure
    assert _create_expecting(kit, type(failure), _build_command()) is failure
    stored_attempt = kit.only_attempt()
    assert stored_attempt.status is PaymentAttemptStatus.LINK_CREATION_FAILED
    assert stored_attempt.failure_code is expected_failure_code
    assert kit.audit_event_types() == [AuditEventType.PAYMENT_LINK_CREATION_FAILED]
    assert kit.last_audit_event().details["failure_code"] == expected_failure_code.value
    replay_error = _create_expecting(kit, PaymentLinkCreationFailedError, _build_command())
    assert isinstance(replay_error, PaymentLinkCreationFailedError)
    assert replay_error.failure_code is expected_failure_code
    assert len(kit.payment_gateway.create_link_calls) == 1


def test_create_payment_link_for_an_offer_not_quoted_raises_and_stores_nothing(
    kit: ServiceTestKit,
) -> None:
    """An offer id the gateway does not quote for the item is OFFER_NOT_FOUND."""
    _create_expecting(kit, OfferNotFoundError, _build_command(offer_id="offer-plan-z"))
    assert kit.database.payment_attempts_by_id == {}
    assert kit.payment_gateway.create_link_calls == []


def test_create_payment_link_replayed_while_the_first_call_runs_raises_in_progress(
    kit: ServiceTestKit,
) -> None:
    """A key whose first request has not finished yet is a typed conflict, never a second call."""
    kit.store_attempt(
        build_payment_attempt(
            idempotency_key=IDEMPOTENCY_KEY,
            request_fingerprint=_build_command().calculate_request_fingerprint(),
        )
    )
    _create_expecting(kit, PaymentLinkCreationInProgressError, _build_command())
    assert kit.payment_gateway.discover_offers_calls == []


def test_create_payment_link_losing_a_race_on_the_key_raises_in_progress(
    kit: ServiceTestKit,
) -> None:
    """A concurrent request that inserted the same key first wins; this one never calls."""
    kit.payment_gateway.before_discover_offers = lambda: kit.store_attempt(
        build_payment_attempt(
            idempotency_key=IDEMPOTENCY_KEY,
            request_fingerprint=_build_command().calculate_request_fingerprint(),
        )
    )
    _create_expecting(kit, PaymentLinkCreationInProgressError, _build_command())
    assert kit.payment_gateway.create_link_calls == []


def test_create_payment_link_losing_a_race_to_a_finished_request_returns_its_link(
    kit: ServiceTestKit,
) -> None:
    """If the winner already made its link, this request replays it."""
    winning_attempt = build_payment_attempt(
        idempotency_key=IDEMPOTENCY_KEY,
        request_fingerprint=_build_command().calculate_request_fingerprint(),
        status=PaymentAttemptStatus.LINK_CREATED,
        gateway_link_id="fake-link-winner",
        payment_link_url="https://fake-gateway.invalid/pay/winner",
    )
    kit.payment_gateway.before_discover_offers = lambda: kit.store_attempt(winning_attempt)
    handoff = _build_service(kit).create_payment_link(_build_command())
    assert (handoff.payment_url, handoff.is_replay) == (winning_attempt.payment_link_url, True)
    assert kit.payment_gateway.create_link_calls == []


def test_create_payment_link_colliding_on_another_unique_column_reraises(
    kit: ServiceTestKit,
) -> None:
    """A clash that is not on the key (here the order id) is not a replay; the error propagates."""
    kit.payment_gateway.before_discover_offers = lambda: kit.store_attempt(
        build_payment_attempt(order_id=EXPECTED_ORDER_ID, idempotency_key="another-key")
    )
    _create_expecting(kit, PaymentAttemptAlreadyExistsError, _build_command())
    assert kit.payment_gateway.create_link_calls == []
