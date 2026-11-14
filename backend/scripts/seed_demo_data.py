"""Seeds the demo shop of DESIGN_SPEC section 4 into the configured database (`make seed`).

The pairing PIN is read from DEMO_MERCHANT_PIN (6 digits) and is never written in code. The
products carry the Mock gateway's demo product ids, so their offers match the M2 counter list.
Running the seed again changes nothing but the PIN and names. The report history step writes
the design week (scripts/demo_report_history.py) once: a shop that has any sale is left alone,
so to reseed for the current week run `make db-reset seed`.
"""

import logging
import os
import re
from collections.abc import Callable, Mapping
from datetime import timedelta
from functools import partial
from zoneinfo import ZoneInfo

from emi_copilot.adapters.payment_gateway.factory import PaymentGatewayFactory
from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_EARBUDS_PRODUCT_ID,
    MOCK_PHONE_64_GB_PRODUCT_ID,
    MOCK_PHONE_128_GB_PRODUCT_ID,
)
from emi_copilot.config.settings import ApplicationSettings, PaymentGatewayMode
from emi_copilot.core.clock import SystemClock
from emi_copilot.core.id_generator import UlidIdGenerator
from emi_copilot.core.logging import configure_logging
from emi_copilot.core.pin_hasher import ScryptPinHasher
from emi_copilot.domain.money import Money
from emi_copilot.repositories.database import create_database_engine, create_session_factory
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.demo_merchant_seed_service import (
    DemoMerchantSeed,
    DemoMerchantSeedService,
    DemoProductSeed,
)
from emi_copilot.services.demo_report_history_seed_service import DemoReportHistorySeedService
from scripts.demo_report_history import DEMO_REPORT_HISTORY

DEMO_MERCHANT_PIN_VARIABLE = "DEMO_MERCHANT_PIN"
DEMO_MERCHANT_PIN_PATTERN = re.compile(r"[0-9]{6}")
MOCK_DEMO_BRAND_ID = "mock-brand-example"
DEMO_SHOP_CODE = "RAVI-0193"

seed_logger = logging.getLogger("emi_copilot.seed")


class DemoSeedConfigurationError(SystemExit):
    """Stops the seed with a message naming the setting to fix; the PIN value is never shown."""


def read_demo_merchant_pin(environment: Mapping[str, str]) -> str:
    """Gives DEMO_MERCHANT_PIN, or stops the seed when it is unset or not exactly 6 digits."""
    pin = environment.get(DEMO_MERCHANT_PIN_VARIABLE, "")
    if not DEMO_MERCHANT_PIN_PATTERN.fullmatch(pin):
        raise DemoSeedConfigurationError(
            f"{DEMO_MERCHANT_PIN_VARIABLE} must be set to exactly 6 digits before seeding, for "
            "example in .env (see .env.example). The seed never stores a PIN in code."
        )
    return pin


DEMO_PRODUCT_SEEDS = (
    DemoProductSeed(
        name="Example phone, 128 GB",
        list_price=Money.from_rupees("22000"),
        gateway_product_id=MOCK_PHONE_128_GB_PRODUCT_ID,
        gateway_brand_id=MOCK_DEMO_BRAND_ID,
        gateway_category_id="mock-category-phones",
    ),
    DemoProductSeed(
        name="Example phone, 64 GB",
        list_price=Money.from_rupees("18000"),
        gateway_product_id=MOCK_PHONE_64_GB_PRODUCT_ID,
        gateway_brand_id=MOCK_DEMO_BRAND_ID,
        gateway_category_id="mock-category-phones",
    ),
    DemoProductSeed(
        name="Example earbuds",
        list_price=Money.from_rupees("2499"),
        gateway_product_id=MOCK_EARBUDS_PRODUCT_ID,
        gateway_brand_id=MOCK_DEMO_BRAND_ID,
        gateway_category_id="mock-category-audio",
    ),
)
"""The three M2 products at their DESIGN_SPEC list prices, on the Mock's demo product ids."""


def build_demo_merchant_seed(pin: str) -> DemoMerchantSeed:
    """Gives Ravi Electronics (RAVI-0193) on "Counter tablet 1" with the three M2 products."""
    return DemoMerchantSeed(
        shop_code=DEMO_SHOP_CODE,
        display_name="Ravi Electronics",
        counter_device_label="Counter tablet 1",
        pin=pin,
        products=DEMO_PRODUCT_SEEDS,
    )


def seed_demo_merchant(unit_of_work_factory: UnitOfWorkFactory, pin: str) -> None:
    """Seed step: creates or refreshes the demo shop and its catalogue, then logs the outcome."""
    outcome = DemoMerchantSeedService(
        unit_of_work_factory, ScryptPinHasher(), UlidIdGenerator()
    ).seed(build_demo_merchant_seed(pin))
    seed_logger.info(
        "demo merchant seeded",
        extra={
            "merchant_id": outcome.merchant_id,
            "is_new_merchant": outcome.is_new_merchant,
            "added_product_count": outcome.added_product_count,
        },
    )


def seed_report_history(unit_of_work_factory: UnitOfWorkFactory, pin: str) -> None:
    """Seed step: writes the design week of sales once, quoted by the Mock gateway.

    The history names the Mock's demo products, so in paytm mode it is skipped with a warning.
    """
    del pin
    settings = ApplicationSettings()
    if settings.payment_gateway_mode is not PaymentGatewayMode.MOCK:
        seed_logger.warning("demo report history skipped: it needs PAYMENT_GATEWAY_MODE=mock")
        return
    clock = SystemClock()
    id_generator = UlidIdGenerator()
    outcome = DemoReportHistorySeedService(
        unit_of_work_factory=unit_of_work_factory,
        payment_gateway=PaymentGatewayFactory().create(settings, clock, id_generator),
        clock=clock,
        id_generator=id_generator,
        time_zone=ZoneInfo(settings.reporting_time_zone),
        choosing_lifetime=timedelta(seconds=settings.sale_choosing_expiry_in_seconds),
    ).seed(DEMO_SHOP_CODE, DEMO_REPORT_HISTORY)
    seed_logger.info(
        "demo report history seeded", extra={"added_sale_count": outcome.added_sale_count}
    )


DEMO_SEED_STEPS: tuple[Callable[[UnitOfWorkFactory, str], None], ...] = (
    seed_demo_merchant,
    seed_report_history,
)
"""Every seed step, in order; each receives the unit-of-work factory and the demo PIN."""


def seed_demo_data(environment: Mapping[str, str]) -> None:
    """Reads the PIN, then runs every seed step against the database named in the settings."""
    settings = ApplicationSettings()
    configure_logging(settings.log_level)
    pin = read_demo_merchant_pin(environment)
    database_engine = create_database_engine(settings)
    try:
        unit_of_work_factory = partial(
            SqlAlchemyUnitOfWork, create_session_factory(database_engine), SystemClock()
        )
        for seed_step in DEMO_SEED_STEPS:
            seed_step(unit_of_work_factory, pin)
    finally:
        database_engine.dispose()


if __name__ == "__main__":
    seed_demo_data(os.environ)
