"""Sale entity: starting, agreeing, expiring, QR re-issue and tolerant payment reports."""

from dataclasses import replace
from datetime import timedelta

import pytest

from emi_copilot.domain.errors import IllegalSaleTransitionError, InvalidSaleDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.sales import (
    PaymentOutcomeEffect,
    Sale,
    SaleIdempotency,
    SalePaymentOutcome,
    SaleStatus,
    SessionCode,
)
from tests.merchant_builders import MERCHANT_ID
from tests.sale_builders import (
    CHOOSING_LIFETIME,
    PRODUCT_ID,
    SALE_ID,
    SALE_STARTED_AT,
    build_no_cost_chosen_plan,
    build_qr_token_state,
    build_sale,
    build_standard_chosen_plan,
)

LATER = SALE_STARTED_AT + timedelta(minutes=5)
SAMPLE_IDEMPOTENCY = SaleIdempotency("sale-key-0001", "f" * 64)


def test_start_gives_a_choosing_sale_with_no_plan_changed_when_it_started() -> None:
    """A new sale is CHOOSING, has no plan, and its status dates from its start."""
    sale = Sale.start(
        sale_id=SALE_ID,
        merchant_id=MERCHANT_ID,
        product_id=PRODUCT_ID,
        price=Money.from_rupees("22000"),
        session_code=SessionCode("0042"),
        qr_token=build_qr_token_state(),
        started_at=SALE_STARTED_AT,
        idempotency=SAMPLE_IDEMPOTENCY,
    )
    assert sale == build_sale(session_code=SessionCode("0042"), idempotency=SAMPLE_IDEMPOTENCY)
    assert sale.status is SaleStatus.CHOOSING
    assert sale.chosen_plan is None
    assert sale.status_changed_at == SALE_STARTED_AT


def test_agree_to_plan_moves_to_ready_to_pay_with_the_plan_and_the_moment() -> None:
    """The agreed plan is kept as shown and the status change is stamped."""
    agreed_sale = build_sale().agree_to_plan(build_standard_chosen_plan(), LATER)
    assert agreed_sale.status is SaleStatus.READY_TO_PAY
    assert agreed_sale.chosen_plan == build_standard_chosen_plan()
    assert agreed_sale.status_changed_at == LATER


def test_agree_to_plan_twice_raises_a_state_conflict() -> None:
    """A second agreement is refused; the first plan stays the evidence."""
    agreed_sale = build_sale().agree_to_plan(build_no_cost_chosen_plan(), LATER)
    with pytest.raises(IllegalSaleTransitionError):
        agreed_sale.agree_to_plan(build_standard_chosen_plan(), LATER)


def test_agree_to_plan_quoted_on_another_price_raises() -> None:
    """A plan priced for a different amount than the sale cannot be agreed to."""
    sale_at_other_price = build_sale(price=Money.from_rupees("18000"))
    with pytest.raises(InvalidSaleDataError, match="sale's price"):
        sale_at_other_price.agree_to_plan(build_no_cost_chosen_plan(), LATER)


def test_issue_qr_token_replaces_the_token_and_keeps_the_status() -> None:
    """Re-issuing a QR code voids the old token by replacing its hash."""
    new_token = build_qr_token_state(nonce_hash="1" * 64)
    reissued_sale = build_sale().issue_qr_token(new_token)
    assert reissued_sale.qr_token == new_token
    assert reissued_sale.status is SaleStatus.CHOOSING
    assert reissued_sale.status_changed_at == SALE_STARTED_AT


@pytest.mark.parametrize(
    "status",
    [
        SaleStatus.READY_TO_PAY,
        SaleStatus.PAID,
        SaleStatus.PAYMENT_NOT_COMPLETED,
        SaleStatus.EXPIRED,
    ],
)
def test_issue_qr_token_outside_choosing_raises(status: SaleStatus) -> None:
    """Once the customer agreed (or the sale expired) no new QR code is issued."""
    with pytest.raises(IllegalSaleTransitionError):
        build_sale(status=status).issue_qr_token(build_qr_token_state(nonce_hash="1" * 64))


def test_expire_moves_choosing_to_expired_without_a_plan() -> None:
    """An unchosen sale expires and still holds no plan."""
    expired_sale = build_sale().expire(LATER)
    assert (expired_sale.status, expired_sale.chosen_plan) == (SaleStatus.EXPIRED, None)


def test_retry_payment_moves_back_to_ready_to_pay_keeping_the_agreed_plan() -> None:
    """After a payment did not go through, the same plan is offered for payment again."""
    retried_sale = build_sale(status=SaleStatus.PAYMENT_NOT_COMPLETED).retry_payment(LATER)
    assert retried_sale.status is SaleStatus.READY_TO_PAY
    assert retried_sale.chosen_plan == build_no_cost_chosen_plan()


@pytest.mark.parametrize(
    ("elapsed", "expected_overdue"),
    [
        (CHOOSING_LIFETIME - timedelta(microseconds=1), False),
        (CHOOSING_LIFETIME, True),
        (CHOOSING_LIFETIME + timedelta(seconds=1), True),
    ],
)
def test_is_choosing_overdue_counts_the_deadline_itself_as_overdue(
    elapsed: timedelta, *, expected_overdue: bool
) -> None:
    """At exactly 3600 s after the start a CHOOSING sale is overdue; a microsecond before, not."""
    now = SALE_STARTED_AT + elapsed
    assert build_sale().is_choosing_overdue(now, CHOOSING_LIFETIME) is expected_overdue


def test_is_choosing_overdue_is_false_once_the_customer_agreed() -> None:
    """Only CHOOSING sales ever expire."""
    long_after = SALE_STARTED_AT + timedelta(days=2)
    agreed_sale = build_sale(status=SaleStatus.READY_TO_PAY)
    assert agreed_sale.is_choosing_overdue(long_after, CHOOSING_LIFETIME) is False


def test_apply_payment_outcome_paid_moves_ready_to_pay_to_paid() -> None:
    """A confirmed payment marks the sale paid at the report's moment."""
    paid_sale, effect = build_sale(status=SaleStatus.READY_TO_PAY).apply_payment_outcome(
        SalePaymentOutcome.PAID, LATER
    )
    assert (paid_sale.status, paid_sale.status_changed_at) == (SaleStatus.PAID, LATER)
    assert effect is PaymentOutcomeEffect.STATUS_CHANGED


@pytest.mark.parametrize(
    ("status", "expected_effect"),
    [
        (SaleStatus.PAID, PaymentOutcomeEffect.NO_CHANGE),
        (SaleStatus.CHOOSING, PaymentOutcomeEffect.IGNORED_NOT_AWAITING_PAYMENT),
    ],
)
def test_apply_payment_outcome_without_a_move_returns_the_same_sale(
    status: SaleStatus, expected_effect: PaymentOutcomeEffect
) -> None:
    """A late failure on a paid sale, or any report on a choosing one, changes nothing."""
    sale = build_sale(status=status)
    unchanged_sale, effect = sale.apply_payment_outcome(SalePaymentOutcome.NOT_COMPLETED, LATER)
    assert unchanged_sale is sale
    assert effect is expected_effect


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("id", " "),
        ("merchant_id", ""),
        ("product_id", ""),
        ("price", Money.from_paise(0)),
        ("price", Money.from_rupees("0.001")),
        ("session_code", "4821"),
        ("status", "CHOOSING"),
        ("qr_token", None),
        ("started_at", SALE_STARTED_AT.replace(tzinfo=None)),
        ("status_changed_at", SALE_STARTED_AT - timedelta(seconds=1)),
    ],
)
def test_sale_with_an_invalid_field_raises(field_name: str, value: object) -> None:
    """Every field is checked when a sale is built."""
    with pytest.raises(InvalidSaleDataError):
        replace(build_sale(), **{field_name: value})  # type: ignore[arg-type]


def test_sale_with_a_plan_while_choosing_raises() -> None:
    """A plan appears only once the customer agrees to one."""
    with pytest.raises(InvalidSaleDataError, match="exactly once"):
        build_sale(chosen_plan=build_no_cost_chosen_plan())


@pytest.mark.parametrize(
    "status", [SaleStatus.READY_TO_PAY, SaleStatus.PAID, SaleStatus.PAYMENT_NOT_COMPLETED]
)
def test_sale_without_a_plan_after_agreement_raises(status: SaleStatus) -> None:
    """Every status after agreement keeps the agreed plan as evidence."""
    with pytest.raises(InvalidSaleDataError, match="exactly once"):
        build_sale(status=status, chosen_plan=None)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("nonce_hash", "E" * 64),
        ("nonce_hash", "e" * 63),
        ("expires_at", SALE_STARTED_AT.replace(tzinfo=None)),
        ("exchanged_at", SALE_STARTED_AT.replace(tzinfo=None)),
    ],
)
def test_qr_token_state_with_an_invalid_field_raises(field_name: str, value: object) -> None:
    """The nonce hash is a lowercase SHA-256 hex digest and every moment has a time zone."""
    with pytest.raises(InvalidSaleDataError):
        build_qr_token_state(**{field_name: value})


def test_qr_token_state_keeps_an_exchange_moment() -> None:
    """Layer 3 records when the phone traded the token in."""
    exchanged_token = build_qr_token_state(exchanged_at=LATER)
    assert exchanged_token.exchanged_at == LATER


@pytest.mark.parametrize(
    ("idempotency_key", "request_fingerprint"), [(" ", "f" * 64), ("sale-key-0001", "not-hex")]
)
def test_sale_idempotency_with_a_blank_key_or_bad_fingerprint_raises(
    idempotency_key: str, request_fingerprint: str
) -> None:
    """The key is non-blank text and the fingerprint a SHA-256 hex digest."""
    with pytest.raises(InvalidSaleDataError):
        SaleIdempotency(idempotency_key, request_fingerprint)
