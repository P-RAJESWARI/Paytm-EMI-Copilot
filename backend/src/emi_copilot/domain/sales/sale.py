"""Sale entity: one customer's EMI purchase at the counter, from the QR code to the payment."""

import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Self

from emi_copilot.domain.errors import InvalidSaleDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_positive_whole_paise_money,
    require_timezone_aware_moment,
)
from emi_copilot.domain.sales.chosen_plan import ChosenPlan
from emi_copilot.domain.sales.sale_state_machine import (
    PaymentOutcomeEffect,
    SaleCommand,
    SalePaymentOutcome,
    SaleStateMachine,
)
from emi_copilot.domain.sales.sale_status import STATUSES_WITH_CHOSEN_PLAN, SaleStatus
from emi_copilot.domain.sales.session_code import SessionCode

_SHA256_HEX_PATTERN = re.compile(r"[0-9a-f]{64}")
_SALE_STATE_MACHINE = SaleStateMachine()


def _require_sha256_hex(value: object, description: str) -> None:
    """Raises unless the value is a lowercase hex SHA-256 digest."""
    if not isinstance(value, str) or _SHA256_HEX_PATTERN.fullmatch(value) is None:
        raise InvalidSaleDataError(f"The {description} must be a lowercase hex SHA-256 digest.")


# Pattern: Value Object. The current customer QR token, known only by its nonce's hash.
@dataclass(frozen=True, slots=True)
class CustomerQrTokenState:
    """The QR token now valid for a sale: its nonce hash, its expiry and when it was exchanged.

    The raw token is never stored; issuing a new one replaces the hash, which voids the old
    token. exchanged_at is set by Layer 3 when the customer's phone trades the token in.
    """

    nonce_hash: str
    expires_at: datetime
    exchanged_at: datetime | None = None

    def __post_init__(self) -> None:
        """Rejects a malformed nonce hash and moments without a time zone."""
        _require_sha256_hex(self.nonce_hash, "QR token nonce hash")
        require_timezone_aware_moment(self.expires_at, "QR token expiry", InvalidSaleDataError)
        if self.exchanged_at is not None:
            require_timezone_aware_moment(
                self.exchanged_at, "QR token exchange", InvalidSaleDataError
            )


# Pattern: Value Object. Ties a started sale to the Idempotency-Key that started it (ADR 0005).
@dataclass(frozen=True, slots=True)
class SaleIdempotency:
    """The Idempotency-Key a sale was started with and the SHA-256 of that request's body."""

    idempotency_key: str
    request_fingerprint: str

    def __post_init__(self) -> None:
        """Rejects a blank key and a malformed fingerprint."""
        require_non_empty_text(self.idempotency_key, "idempotency key", InvalidSaleDataError)
        _require_sha256_hex(self.request_fingerprint, "request fingerprint")


@dataclass(frozen=True, slots=True)
class Sale:
    """A sale of one product at its counter price; every move goes through SaleStateMachine.

    It is immutable: each command returns a new Sale that the repository saves. A chosen plan
    exists exactly when the customer has agreed to one, and it is always on this sale's price.
    """

    id: str
    merchant_id: str
    product_id: str
    price: Money
    session_code: SessionCode
    status: SaleStatus
    chosen_plan: ChosenPlan | None
    qr_token: CustomerQrTokenState
    started_at: datetime
    status_changed_at: datetime
    idempotency: SaleIdempotency | None = None

    def __post_init__(self) -> None:
        """Rejects blank ids, a zero price, bad timestamps and a plan in the wrong status."""
        for text, description in (
            (self.id, "sale id"),
            (self.merchant_id, "merchant id"),
            (self.product_id, "product id"),
        ):
            require_non_empty_text(text, description, InvalidSaleDataError)
        require_positive_whole_paise_money(self.price, "price", InvalidSaleDataError)
        for value, value_type in (
            (self.session_code, SessionCode),
            (self.status, SaleStatus),
            (self.qr_token, CustomerQrTokenState),
        ):
            if not isinstance(value, value_type):
                raise InvalidSaleDataError(f"A sale needs a {value_type.__name__}.")
        require_timezone_aware_moment(self.started_at, "start", InvalidSaleDataError)
        require_timezone_aware_moment(self.status_changed_at, "status change", InvalidSaleDataError)
        if self.status_changed_at < self.started_at:
            raise InvalidSaleDataError("A sale's status cannot change before the sale started.")
        self._require_chosen_plan_matches_status()

    def _require_chosen_plan_matches_status(self) -> None:
        """Raises unless a plan on this price is held exactly in the statuses that need one."""
        has_chosen_plan = self.chosen_plan is not None
        if has_chosen_plan != (self.status in STATUSES_WITH_CHOSEN_PLAN):
            raise InvalidSaleDataError(
                "A sale holds a chosen plan exactly once the customer has agreed to one."
            )
        if self.chosen_plan is not None and self.chosen_plan.price != self.price:
            raise InvalidSaleDataError("The chosen plan must be quoted on the sale's price.")

    @classmethod
    def start(  # noqa: PLR0913 - a new sale is defined by exactly these facts
        cls,
        *,
        sale_id: str,
        merchant_id: str,
        product_id: str,
        price: Money,
        session_code: SessionCode,
        qr_token: CustomerQrTokenState,
        started_at: datetime,
        idempotency: SaleIdempotency | None,
    ) -> Self:
        """Starts a sale in CHOOSING with no plan, its first QR token and its start moment."""
        return cls(
            id=sale_id,
            merchant_id=merchant_id,
            product_id=product_id,
            price=price,
            session_code=session_code,
            status=SaleStatus.CHOOSING,
            chosen_plan=None,
            qr_token=qr_token,
            started_at=started_at,
            status_changed_at=started_at,
            idempotency=idempotency,
        )

    def is_choosing_overdue(self, now: datetime, choosing_lifetime: timedelta) -> bool:
        """Tells whether the sale is still CHOOSING at or after started_at + choosing_lifetime.

        The deadline itself counts as overdue, as for QR tokens and device tokens.
        """
        return self.status is SaleStatus.CHOOSING and now >= self.started_at + choosing_lifetime

    def agree_to_plan(self, chosen_plan: ChosenPlan, now: datetime) -> Self:
        """Records the customer's agreed plan and moves CHOOSING to READY_TO_PAY."""
        return self._moved_by(SaleCommand.AGREE_TO_PLAN, now, chosen_plan=chosen_plan)

    def issue_qr_token(self, qr_token: CustomerQrTokenState) -> Self:
        """Replaces the QR token while CHOOSING, voiding the previous one; the status stays."""
        _SALE_STATE_MACHINE.status_after_command(self.status, SaleCommand.ISSUE_QR_CODE)
        return replace(self, qr_token=qr_token)

    def expire(self, now: datetime) -> Self:
        """Moves a sale nobody agreed to in time from CHOOSING to EXPIRED."""
        return self._moved_by(SaleCommand.EXPIRE, now)

    def retry_payment(self, now: datetime) -> Self:
        """Moves PAYMENT_NOT_COMPLETED back to READY_TO_PAY, keeping the agreed plan."""
        return self._moved_by(SaleCommand.RETRY_PAYMENT, now)

    def apply_payment_outcome(
        self, outcome: SalePaymentOutcome, now: datetime
    ) -> tuple[Self, PaymentOutcomeEffect]:
        """Applies a gateway payment report; it never raises, and only a change gives a new Sale."""
        decision = _SALE_STATE_MACHINE.decide_payment_outcome(self.status, outcome)
        if decision.effect is not PaymentOutcomeEffect.STATUS_CHANGED:
            return self, decision.effect
        return replace(self, status=decision.status, status_changed_at=now), decision.effect

    def _moved_by(
        self, command: SaleCommand, now: datetime, chosen_plan: ChosenPlan | None = None
    ) -> Self:
        """Applies a strict command; an agreed plan, once set, is kept unless one is given."""
        next_status = _SALE_STATE_MACHINE.status_after_command(self.status, command)
        return replace(
            self,
            status=next_status,
            status_changed_at=now,
            chosen_plan=chosen_plan or self.chosen_plan,
        )
