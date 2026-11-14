"""AuthenticateMerchantService: turns a bearer token into the merchant it signs in."""

from emi_copilot.core.clock import Clock
from emi_copilot.core.opaque_token import hash_opaque_token
from emi_copilot.domain.errors import MerchantAuthenticationRequiredError
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.pair_device_service import build_merchant_principal

# One detail for every refused token, so a probe cannot tell unknown from expired or revoked.
AUTHENTICATION_REQUIRED_DETAIL = "A valid merchant bearer token is required; pair the device again."


class AuthenticateMerchantService:
    """Looks a token up by its SHA-256 and accepts it only while unexpired and not revoked."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        """Keeps the unit-of-work factory and the clock that decides expiry."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def authenticate(self, access_token: str) -> MerchantPrincipal:
        """Gives the principal of a usable token, or raises MerchantAuthenticationRequiredError."""
        now = self._clock.now()
        with self._unit_of_work_factory() as unit_of_work:
            device_pairing = unit_of_work.device_pairings.find_by_access_token_hash(
                hash_opaque_token(access_token)
            )
            if device_pairing is None or not device_pairing.is_usable_at(now):
                raise MerchantAuthenticationRequiredError(AUTHENTICATION_REQUIRED_DETAIL)
            merchant = unit_of_work.merchants.find_by_id(device_pairing.merchant_id)
        if merchant is None:
            raise MerchantAuthenticationRequiredError(AUTHENTICATION_REQUIRED_DETAIL)
        return build_merchant_principal(merchant, device_pairing)
