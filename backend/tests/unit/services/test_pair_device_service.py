"""PairDeviceService: PIN check with lockout, one answer for unknown shops, token hash stored."""

import logging
from dataclasses import replace
from datetime import timedelta

import pytest

from emi_copilot.core.opaque_token import hash_opaque_token
from emi_copilot.core.pin_hasher import ScryptPinHasher
from emi_copilot.domain.errors import (
    InvalidPairingCredentialsError,
    PairingTemporarilyLockedError,
)
from emi_copilot.domain.merchants import (
    UNLOCKED_PIN_ATTEMPT_STATE,
    MerchantPrincipal,
    PinAttemptState,
)
from emi_copilot.services.pair_device_service import (
    INVALID_CREDENTIALS_DETAIL,
    PairDeviceCommand,
    PairDeviceService,
)
from tests.merchant_builders import MERCHANT_ID, build_merchant
from tests.payment_builders import CREATED_AT
from tests.unit.services.conftest import ServiceTestKit

SYNTHETIC_PIN = "135790"
WRONG_PIN = "864209"
SHOP_CODE = "SHOP-0001"
TWELVE_HOURS = timedelta(hours=12)


@pytest.fixture(scope="module")
def pin_hasher() -> ScryptPinHasher:
    """Builds one real hasher for the module; scrypt is fast enough for unit tests."""
    return ScryptPinHasher()


@pytest.fixture
def service(kit: ServiceTestKit, pin_hasher: ScryptPinHasher) -> PairDeviceService:
    """Stores one shop whose PIN is SYNTHETIC_PIN and builds the service with a 12-hour token."""
    hashed_pin = pin_hasher.hash_new_pin(SYNTHETIC_PIN)
    kit.database.merchants_by_id[MERCHANT_ID] = build_merchant(
        pin_hash_hex=hashed_pin.hash_hex, pin_salt_hex=hashed_pin.salt_hex
    )
    return PairDeviceService(
        kit.unit_of_work_factory, pin_hasher, kit.clock, kit.id_generator, TWELVE_HOURS
    )


def stored_attempt_state(kit: ServiceTestKit) -> PinAttemptState:
    """Reads the shop's committed PIN attempt state."""
    return kit.database.merchants_by_id[MERCHANT_ID].pin_attempt_state


def pair(service: PairDeviceService, pin: str, shop_code: str = SHOP_CODE) -> MerchantPrincipal:
    """Pairs with the PIN and gives the signed-in principal."""
    return service.pair_device(PairDeviceCommand(shop_code=shop_code, pin=pin)).principal


def test_pair_device_with_right_pin_issues_a_token_stored_only_as_its_hash(
    service: PairDeviceService, kit: ServiceTestKit
) -> None:
    """The token comes back once; the store keeps its SHA-256 with a 12-hour expiry."""
    result = service.pair_device(PairDeviceCommand(shop_code=SHOP_CODE, pin=SYNTHETIC_PIN))
    (stored_pairing,) = kit.database.device_pairings_by_id.values()
    assert stored_pairing.access_token_hash == hash_opaque_token(result.access_token)
    assert result.access_token not in repr(result)
    assert stored_pairing.expires_at == CREATED_AT + TWELVE_HOURS
    assert stored_pairing.device_label == "Counter tablet 1"
    assert result.principal == MerchantPrincipal(
        merchant_id=MERCHANT_ID,
        shop_code=SHOP_CODE,
        shop_name="Synthetic Electronics",
        device_pairing_id=stored_pairing.id,
        device_label="Counter tablet 1",
        access_expires_at=CREATED_AT + TWELVE_HOURS,
    )


def test_pair_device_twice_issues_two_distinct_tokens(service: PairDeviceService) -> None:
    """Each pairing is a separate device session with its own token."""
    first_result = service.pair_device(PairDeviceCommand(shop_code=SHOP_CODE, pin=SYNTHETIC_PIN))
    second_result = service.pair_device(PairDeviceCommand(shop_code=SHOP_CODE, pin=SYNTHETIC_PIN))
    assert first_result.access_token != second_result.access_token


def test_pair_device_with_wrong_pin_refuses_and_commits_the_failure(
    service: PairDeviceService, kit: ServiceTestKit
) -> None:
    """The failure count is saved even though the request is refused."""
    with pytest.raises(InvalidPairingCredentialsError):
        pair(service, WRONG_PIN)
    assert stored_attempt_state(kit) == PinAttemptState(
        consecutive_failure_count=1, locked_until=None
    )
    assert kit.database.device_pairings_by_id == {}


def test_pair_device_with_unknown_shop_gives_the_wrong_pin_answer_after_one_pin_check(
    service: PairDeviceService, pin_hasher: ScryptPinHasher, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same error and detail as a wrong PIN, and the decoy PIN check runs once."""
    decoy_checks: list[str] = []
    monkeypatch.setattr(pin_hasher, "spend_time_of_one_pin_check", decoy_checks.append)
    with pytest.raises(InvalidPairingCredentialsError) as unknown_shop_error:
        pair(service, SYNTHETIC_PIN, shop_code="SHOP-9999")
    with pytest.raises(InvalidPairingCredentialsError) as wrong_pin_error:
        pair(service, WRONG_PIN)
    assert unknown_shop_error.value.detail == wrong_pin_error.value.detail
    assert unknown_shop_error.value.detail == INVALID_CREDENTIALS_DETAIL
    assert decoy_checks == [SYNTHETIC_PIN]


def test_pair_device_fifth_wrong_pin_locks_and_sixth_attempt_is_refused_with_right_pin(
    service: PairDeviceService, kit: ServiceTestKit
) -> None:
    """Wrong PINs 1 to 5 answer 401; then even the right PIN is locked out for 15 minutes."""
    for _ in range(5):
        with pytest.raises(InvalidPairingCredentialsError):
            pair(service, WRONG_PIN)
    assert stored_attempt_state(kit).locked_until == CREATED_AT + timedelta(minutes=15)
    with pytest.raises(PairingTemporarilyLockedError) as locked_error:
        pair(service, SYNTHETIC_PIN)
    assert locked_error.value.retry_after_in_seconds == 15 * 60
    assert kit.database.device_pairings_by_id == {}


def test_pair_device_after_the_lock_ends_accepts_the_right_pin_and_resets(
    service: PairDeviceService, kit: ServiceTestKit
) -> None:
    """Once 15 minutes have passed the right PIN pairs and the attempt state is clean."""
    for _ in range(5):
        with pytest.raises(InvalidPairingCredentialsError):
            pair(service, WRONG_PIN)
    kit.clock.advance(timedelta(minutes=14, seconds=59))
    with pytest.raises(PairingTemporarilyLockedError) as locked_error:
        pair(service, SYNTHETIC_PIN)
    assert locked_error.value.retry_after_in_seconds == 1
    kit.clock.advance(timedelta(seconds=1))
    assert pair(service, SYNTHETIC_PIN).merchant_id == MERCHANT_ID
    assert stored_attempt_state(kit) == UNLOCKED_PIN_ATTEMPT_STATE


def test_pair_device_right_pin_after_some_failures_resets_the_count(
    service: PairDeviceService, kit: ServiceTestKit
) -> None:
    """Failures must be consecutive to lock: a success in between wipes them."""
    for _ in range(4):
        with pytest.raises(InvalidPairingCredentialsError):
            pair(service, WRONG_PIN)
    pair(service, SYNTHETIC_PIN)
    assert stored_attempt_state(kit) == UNLOCKED_PIN_ATTEMPT_STATE
    with pytest.raises(InvalidPairingCredentialsError):
        pair(service, WRONG_PIN)
    assert stored_attempt_state(kit).consecutive_failure_count == 1


def test_pair_device_with_clean_record_does_not_rewrite_the_shop(
    service: PairDeviceService, kit: ServiceTestKit
) -> None:
    """A first-time success leaves the stored shop exactly as it was."""
    stored_merchant = kit.database.merchants_by_id[MERCHANT_ID]
    pair(service, SYNTHETIC_PIN)
    assert kit.database.merchants_by_id[MERCHANT_ID] is stored_merchant


def test_pair_device_while_locked_does_not_extend_the_lock(
    service: PairDeviceService, kit: ServiceTestKit
) -> None:
    """Hammering a locked shop with wrong PINs leaves its lock end where it was."""
    kit.database.merchants_by_id[MERCHANT_ID] = replace(
        kit.database.merchants_by_id[MERCHANT_ID],
        pin_attempt_state=PinAttemptState(
            consecutive_failure_count=0, locked_until=CREATED_AT + timedelta(minutes=5)
        ),
    )
    with pytest.raises(PairingTemporarilyLockedError):
        pair(service, WRONG_PIN)
    assert stored_attempt_state(kit).locked_until == CREATED_AT + timedelta(minutes=5)


def test_pair_device_logs_the_lock_and_the_pairing_without_pin_or_token(
    service: PairDeviceService, caplog: pytest.LogCaptureFixture
) -> None:
    """Security events are logged by merchant id; no PIN or token reaches any record."""
    with caplog.at_level(logging.INFO, logger="emi_copilot.services.pair_device_service"):
        for _ in range(5):
            with pytest.raises(InvalidPairingCredentialsError):
                pair(service, WRONG_PIN)
    lock_records = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert [record.getMessage() for record in lock_records] == [
        "pairing locked after repeated wrong PINs"
    ]
    assert all(WRONG_PIN not in str(record.__dict__) for record in caplog.records)


def test_pair_device_success_log_never_holds_the_token(
    service: PairDeviceService, caplog: pytest.LogCaptureFixture
) -> None:
    """The success event names the merchant and pairing ids only."""
    with caplog.at_level(logging.INFO, logger="emi_copilot.services.pair_device_service"):
        result = service.pair_device(PairDeviceCommand(shop_code=SHOP_CODE, pin=SYNTHETIC_PIN))
    (record,) = caplog.records
    assert record.getMessage() == "merchant device paired"
    assert result.access_token not in str(record.__dict__)
    assert SYNTHETIC_PIN not in str(record.__dict__)


def test_pair_device_command_repr_hides_the_pin() -> None:
    """A command that ends up in a log or traceback never shows the PIN."""
    assert SYNTHETIC_PIN not in repr(PairDeviceCommand(shop_code=SHOP_CODE, pin=SYNTHETIC_PIN))
