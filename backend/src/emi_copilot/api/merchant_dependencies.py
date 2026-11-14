"""Providers of the merchant pairing, sign-in and catalogue services, assembled per request.

Kept beside dependencies.py (the composition root) so neither file outgrows its size limit;
the components themselves are still built only there.
"""

from datetime import timedelta
from typing import Annotated

from fastapi import Depends

from emi_copilot.api.dependencies import (
    ClockDependency,
    ComponentsDependency,
    IdGeneratorDependency,
    OfferDiscoveryServiceDependency,
    UnitOfWorkFactoryDependency,
)
from emi_copilot.core.pin_hasher import ScryptPinHasher
from emi_copilot.services.authenticate_merchant_service import AuthenticateMerchantService
from emi_copilot.services.pair_device_service import PairDeviceService
from emi_copilot.services.product_catalogue_service import ProductCatalogueService


def provide_pin_hasher(components: ComponentsDependency) -> ScryptPinHasher:
    """Gives the PIN hasher built at startup with its decoy hash."""
    return components.pin_hasher


def provide_access_token_lifetime(components: ComponentsDependency) -> timedelta:
    """Gives how long a paired device's bearer token lasts."""
    return timedelta(seconds=components.settings.merchant_access_token_lifetime_in_seconds)


PinHasherDependency = Annotated[ScryptPinHasher, Depends(provide_pin_hasher)]
AccessTokenLifetimeDependency = Annotated[timedelta, Depends(provide_access_token_lifetime)]


def provide_pair_device_service(
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    pin_hasher: PinHasherDependency,
    clock: ClockDependency,
    id_generator: IdGeneratorDependency,
    access_token_lifetime: AccessTokenLifetimeDependency,
) -> PairDeviceService:
    """Assembles the device pairing service from the injected components."""
    return PairDeviceService(
        unit_of_work_factory, pin_hasher, clock, id_generator, access_token_lifetime
    )


def provide_authenticate_merchant_service(
    unit_of_work_factory: UnitOfWorkFactoryDependency, clock: ClockDependency
) -> AuthenticateMerchantService:
    """Assembles the merchant authentication service from the injected components."""
    return AuthenticateMerchantService(unit_of_work_factory, clock)


def provide_product_catalogue_service(
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    offer_discovery_service: OfferDiscoveryServiceDependency,
) -> ProductCatalogueService:
    """Assembles the product catalogue service on top of offer discovery."""
    return ProductCatalogueService(unit_of_work_factory, offer_discovery_service)


PairDeviceServiceDependency = Annotated[PairDeviceService, Depends(provide_pair_device_service)]
AuthenticateMerchantServiceDependency = Annotated[
    AuthenticateMerchantService, Depends(provide_authenticate_merchant_service)
]
ProductCatalogueServiceDependency = Annotated[
    ProductCatalogueService, Depends(provide_product_catalogue_service)
]
