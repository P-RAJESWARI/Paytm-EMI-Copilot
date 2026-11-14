"""PairDeviceService: trades a shop id and PIN for a counter device's bearer token."""

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.core.opaque_token import issue_opaque_token
from emi_copilot.core.pin_hasher import HashedPin, ScryptPinHasher
from emi_copilot.domain.errors import (
    DomainError,
    InvalidPairingCredentialsError,
    PairingTemporarilyLockedError,
)
from emi_copilot.domain.merchants import (
    DevicePairing,
    Merchant,
    MerchantPrincipal,
    PinLockoutPolicy,
)
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork, UnitOfWorkFactory

pair_device_logger = logging.getLogger(__name__)

# One detail for an unknown shop and a wrong PIN, so the answer never tells them apart.
INVALID_CREDENTIALS_DETAIL = "The shop id and PIN do not match a shop."
LOCKED_DETAIL = "Pairing is locked after repeated wrong PINs; try again after Retry-After."


@dataclass(frozen=True, slots=True)
class PairDeviceCommand:
    """The shop id and PIN typed on the counter device; the PIN is kept out of repr."""

    shop_code: str
    pin: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class DevicePairingResult:
    """The new bearer token, shown once and kept out of repr, and whom it signs in."""

    access_token: str = field(repr=False)
    principal: MerchantPrincipal


type PairingOutcome = DevicePairingResult | DomainError
"""What one attempt decided inside its transaction; a refusal is raised after the commit."""


class PairDeviceService:
    """Checks a shop's PIN with lockout and issues a device token whose hash alone is stored.

    An unknown shop spends one PIN check on a decoy hash and gets the same error as a wrong PIN.
    Wrong PINs are counted on the shop's row (locked while it is read), and the count commits
    even though the request is refused, so the lockout survives restarts.
    """

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        pin_hasher: ScryptPinHasher,
        clock: Clock,
        id_generator: IdGenerator,
        access_token_lifetime: timedelta,
    ) -> None:
        """Keeps the collaborators and the token lifetime; lockout uses the default 5 and 15 min."""
        self._unit_of_work_factory = unit_of_work_factory
        self._pin_hasher = pin_hasher
        self._clock = clock
        self._id_generator = id_generator
        self._access_token_lifetime = access_token_lifetime
        self._lockout_policy = PinLockoutPolicy()

    def pair_device(self, command: PairDeviceCommand) -> DevicePairingResult:
        """Pairs the device or raises InvalidPairingCredentialsError or a lockout error."""
        now = self._clock.now()
        with self._unit_of_work_factory() as unit_of_work:
            outcome = self._decide_pairing(unit_of_work, command, now)
        if isinstance(outcome, DomainError):
            raise outcome
        pair_device_logger.info(
            "merchant device paired",
            extra={
                "merchant_id": outcome.principal.merchant_id,
                "device_pairing_id": outcome.principal.device_pairing_id,
            },
        )
        return outcome

    def _decide_pairing(
        self, unit_of_work: UnitOfWork, command: PairDeviceCommand, now: datetime
    ) -> PairingOutcome:
        """Applies the lockout and the PIN check to the shop, writing what the attempt changed."""
        merchant = unit_of_work.merchants.find_by_shop_code_for_update(command.shop_code)
        if merchant is None:
            self._pin_hasher.spend_time_of_one_pin_check(command.pin)
            return InvalidPairingCredentialsError(INVALID_CREDENTIALS_DETAIL)
        seconds_until_unlocked = self._lockout_policy.find_seconds_until_unlocked(
            merchant.pin_attempt_state, now
        )
        if seconds_until_unlocked is not None:
            return PairingTemporarilyLockedError(seconds_until_unlocked, LOCKED_DETAIL)
        stored_pin = HashedPin(hash_hex=merchant.pin_hash_hex, salt_hex=merchant.pin_salt_hex)
        if not self._pin_hasher.is_matching_pin(command.pin, stored_pin):
            self._record_wrong_pin(unit_of_work, merchant, now)
            return InvalidPairingCredentialsError(INVALID_CREDENTIALS_DETAIL)
        return self._issue_device_token(unit_of_work, merchant, now)

    def _record_wrong_pin(
        self, unit_of_work: UnitOfWork, merchant: Merchant, now: datetime
    ) -> None:
        """Counts the wrong PIN on the shop and logs a security event when it locks the shop."""
        attempt_state = self._lockout_policy.record_failed_attempt(merchant.pin_attempt_state, now)
        unit_of_work.merchants.update(replace(merchant, pin_attempt_state=attempt_state))
        if attempt_state.locked_until is not None:
            pair_device_logger.warning(
                "pairing locked after repeated wrong PINs", extra={"merchant_id": merchant.id}
            )

    def _issue_device_token(
        self, unit_of_work: UnitOfWork, merchant: Merchant, now: datetime
    ) -> DevicePairingResult:
        """Resets the shop's failure count, stores the new pairing and returns its token once."""
        attempt_state = self._lockout_policy.record_successful_attempt()
        if merchant.pin_attempt_state != attempt_state:
            unit_of_work.merchants.update(replace(merchant, pin_attempt_state=attempt_state))
        issued_token = issue_opaque_token()
        device_pairing = DevicePairing(
            id=self._id_generator.new_id(),
            merchant_id=merchant.id,
            device_label=merchant.counter_device_label,
            access_token_hash=issued_token.token_hash,
            expires_at=now + self._access_token_lifetime,
            revoked_at=None,
        )
        unit_of_work.device_pairings.add(device_pairing)
        return DevicePairingResult(
            access_token=issued_token.token,
            principal=build_merchant_principal(merchant, device_pairing),
        )


def build_merchant_principal(
    merchant: Merchant, device_pairing: DevicePairing
) -> MerchantPrincipal:
    """Names the shop and device a pairing signs in, with the pairing's expiry."""
    return MerchantPrincipal(
        merchant_id=merchant.id,
        shop_code=merchant.shop_code,
        shop_name=merchant.display_name,
        device_pairing_id=device_pairing.id,
        device_label=device_pairing.device_label,
        access_expires_at=device_pairing.expires_at,
    )
