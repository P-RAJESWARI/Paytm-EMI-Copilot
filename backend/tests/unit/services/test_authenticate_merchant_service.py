"""AuthenticateMerchantService: a token signs in only while unexpired and not revoked."""

from datetime import timedelta

import pytest

from emi_copilot.core.opaque_token import hash_opaque_token
from emi_copilot.domain.errors import MerchantAuthenticationRequiredError
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.services.authenticate_merchant_service import AuthenticateMerchantService
from tests.merchant_builders import MERCHANT_ID, build_device_pairing, build_merchant
from tests.payment_builders import CREATED_AT
from tests.unit.services.conftest import ServiceTestKit

SYNTHETIC_BEARER_VALUE = "synthetic-bearer-value-for-service-tests"


@pytest.fixture
def service(kit: ServiceTestKit) -> AuthenticateMerchantService:
    """Stores a shop with one pairing for SYNTHETIC_BEARER_VALUE, expiring in 12 hours."""
    kit.database.merchants_by_id[MERCHANT_ID] = build_merchant()
    store_pairing(kit)
    return AuthenticateMerchantService(kit.unit_of_work_factory, kit.clock)


def store_pairing(kit: ServiceTestKit, **overrides: object) -> None:
    """Stores the synthetic token's pairing, with fields overridden as given."""
    pairing = build_device_pairing(
        access_token_hash=hash_opaque_token(SYNTHETIC_BEARER_VALUE),
        expires_at=CREATED_AT + timedelta(hours=12),
        **overrides,
    )
    kit.database.device_pairings_by_id[pairing.id] = pairing


def test_authenticate_with_usable_token_gives_the_shop_and_device(
    service: AuthenticateMerchantService,
) -> None:
    """The principal names the shop, its device and the token's expiry."""
    assert service.authenticate(SYNTHETIC_BEARER_VALUE) == MerchantPrincipal(
        merchant_id=MERCHANT_ID,
        shop_code="SHOP-0001",
        shop_name="Synthetic Electronics",
        device_pairing_id="01JCPAIRING000000000000001",
        device_label="Counter tablet 1",
        access_expires_at=CREATED_AT + timedelta(hours=12),
    )


def test_authenticate_with_unknown_token_is_refused(service: AuthenticateMerchantService) -> None:
    """A token that was never issued signs nobody in."""
    with pytest.raises(MerchantAuthenticationRequiredError):
        service.authenticate("synthetic-unknown-bearer-value")


def test_authenticate_at_the_expiry_moment_is_refused(
    service: AuthenticateMerchantService, kit: ServiceTestKit
) -> None:
    """One microsecond before expiry still works; the expiry moment itself does not."""
    kit.clock.advance(timedelta(hours=12) - timedelta(microseconds=1))
    assert service.authenticate(SYNTHETIC_BEARER_VALUE).merchant_id == MERCHANT_ID
    kit.clock.advance(timedelta(microseconds=1))
    with pytest.raises(MerchantAuthenticationRequiredError):
        service.authenticate(SYNTHETIC_BEARER_VALUE)


def test_authenticate_with_revoked_token_is_refused(kit: ServiceTestKit) -> None:
    """Revocation ends a token at once, before its expiry."""
    kit.database.merchants_by_id[MERCHANT_ID] = build_merchant()
    store_pairing(kit, revoked_at=CREATED_AT)
    with pytest.raises(MerchantAuthenticationRequiredError):
        AuthenticateMerchantService(kit.unit_of_work_factory, kit.clock).authenticate(
            SYNTHETIC_BEARER_VALUE
        )


def test_authenticate_when_the_shop_is_gone_is_refused(kit: ServiceTestKit) -> None:
    """A pairing whose merchant no longer exists signs nobody in."""
    store_pairing(kit)
    with pytest.raises(MerchantAuthenticationRequiredError):
        AuthenticateMerchantService(kit.unit_of_work_factory, kit.clock).authenticate(
            SYNTHETIC_BEARER_VALUE
        )


def test_authenticate_refusals_share_one_detail(
    service: AuthenticateMerchantService, kit: ServiceTestKit
) -> None:
    """Unknown and expired tokens give the same answer, so a probe learns nothing."""
    with pytest.raises(MerchantAuthenticationRequiredError) as unknown_error:
        service.authenticate("synthetic-unknown-bearer-value")
    kit.clock.advance(timedelta(days=1))
    with pytest.raises(MerchantAuthenticationRequiredError) as expired_error:
        service.authenticate(SYNTHETIC_BEARER_VALUE)
    assert unknown_error.value.detail == expired_error.value.detail
