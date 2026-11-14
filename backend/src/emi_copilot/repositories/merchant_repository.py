"""Stores and loads merchants, mapping ORM rows to domain entities at this boundary."""

from datetime import UTC, datetime

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from emi_copilot.core.clock import Clock
from emi_copilot.domain.errors import InvalidMerchantDataError
from emi_copilot.domain.merchants import Merchant, PinAttemptState
from emi_copilot.models import MerchantModel


def _in_utc(moment: datetime | None) -> datetime | None:
    """Gives a stored moment in UTC, keeping None as None."""
    return None if moment is None else moment.astimezone(UTC)


def _to_domain(merchant_model: MerchantModel) -> Merchant:
    """Maps an ORM row back to a validated domain entity; the lock end is returned in UTC."""
    return Merchant(
        id=merchant_model.id,
        shop_code=merchant_model.shop_code,
        display_name=merchant_model.display_name,
        counter_device_label=merchant_model.counter_device_label,
        pin_hash_hex=merchant_model.pin_hash,
        pin_salt_hex=merchant_model.pin_salt,
        pin_attempt_state=PinAttemptState(
            consecutive_failure_count=merchant_model.failed_pin_attempt_count,
            locked_until=_in_utc(merchant_model.pin_locked_until),
        ),
    )


# Pattern: Repository. Keeps every merchant query out of services; no business rules here.
class MerchantRepository:
    """Adds, finds and updates merchants inside the unit of work's session."""

    def __init__(self, session: Session, clock: Clock) -> None:
        """Uses the unit of work's session and the injected clock for created_at and updated_at."""
        self._session = session
        self._clock = clock

    def add(self, merchant: Merchant) -> None:
        """Inserts a new merchant now; a duplicate shop code fails on the unique constraint."""
        now = self._clock.now()
        self._session.add(
            MerchantModel(
                id=merchant.id,
                shop_code=merchant.shop_code,
                display_name=merchant.display_name,
                counter_device_label=merchant.counter_device_label,
                pin_hash=merchant.pin_hash_hex,
                pin_salt=merchant.pin_salt_hex,
                failed_pin_attempt_count=merchant.pin_attempt_state.consecutive_failure_count,
                pin_locked_until=merchant.pin_attempt_state.locked_until,
                created_at=now,
                updated_at=now,
            )
        )
        self._session.flush()

    def find_by_id(self, merchant_id: str) -> Merchant | None:
        """Returns the merchant with this id, or None."""
        return self._find_one_where(MerchantModel.id == merchant_id)

    def find_by_shop_code_for_update(self, shop_code: str) -> Merchant | None:
        """Returns the merchant with this shop code, locking its row until the transaction ends.

        Two pairing attempts on one shop then count their failures one after the other, so a
        burst of parallel guesses cannot slip past the lockout.
        """
        return self._find_one_where(MerchantModel.shop_code == shop_code, is_locked=True)

    def lock_for_update(self, merchant_id: str) -> None:
        """Locks the merchant's row until the transaction ends, so its sales start one by one.

        Two sales started at once then never pick the same session code or both miss the same
        Idempotency-Key.
        """
        self._session.execute(
            select(MerchantModel.id).where(MerchantModel.id == merchant_id).with_for_update()
        )

    def update(self, merchant: Merchant) -> None:
        """Saves the mutable fields (names, PIN hash and salt, attempt state); stamps updated_at.

        The id and shop code never change after insertion, so their values are ignored.
        """
        merchant_model = self._session.get(MerchantModel, merchant.id)
        if merchant_model is None:
            raise InvalidMerchantDataError(f"No merchant with id {merchant.id} is stored.")
        merchant_model.display_name = merchant.display_name
        merchant_model.counter_device_label = merchant.counter_device_label
        merchant_model.pin_hash = merchant.pin_hash_hex
        merchant_model.pin_salt = merchant.pin_salt_hex
        merchant_model.failed_pin_attempt_count = (
            merchant.pin_attempt_state.consecutive_failure_count
        )
        merchant_model.pin_locked_until = merchant.pin_attempt_state.locked_until
        merchant_model.updated_at = self._clock.now()
        self._session.flush()

    def _find_one_where(
        self, condition: ColumnElement[bool], *, is_locked: bool = False
    ) -> Merchant | None:
        """Loads at most one merchant matching a condition on a unique column, maybe locking it."""
        statement = select(MerchantModel).where(condition)
        if is_locked:
            statement = statement.with_for_update()
        merchant_model = self._session.scalars(statement).one_or_none()
        return None if merchant_model is None else _to_domain(merchant_model)
