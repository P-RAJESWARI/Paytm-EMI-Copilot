"""The seed script reads the demo PIN from the environment and seeds the DESIGN_SPEC shop."""

import logging
from typing import NoReturn

import pytest

from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_PLAN_DEFINITIONS_BY_PRODUCT_ID,
)
from emi_copilot.domain.money import Money
from scripts.seed_demo_data import (
    DEMO_MERCHANT_PIN_VARIABLE,
    DEMO_SEED_STEPS,
    DemoSeedConfigurationError,
    build_demo_merchant_seed,
    read_demo_merchant_pin,
    seed_demo_merchant,
    seed_report_history,
)

SYNTHETIC_PIN = "135790"


def test_read_demo_merchant_pin_with_six_digits_gives_it() -> None:
    """A 6-digit DEMO_MERCHANT_PIN is used as the demo shop's PIN."""
    assert read_demo_merchant_pin({DEMO_MERCHANT_PIN_VARIABLE: SYNTHETIC_PIN}) == SYNTHETIC_PIN


@pytest.mark.parametrize(
    "environment",
    [{}, {DEMO_MERCHANT_PIN_VARIABLE: ""}, {DEMO_MERCHANT_PIN_VARIABLE: "12345"}],
    ids=["unset", "blank", "five-digits"],
)
def test_read_demo_merchant_pin_unset_or_malformed_stops_with_a_clear_message(
    environment: dict[str, str],
) -> None:
    """Seeding never falls back to a PIN in code; the message names the variable only."""
    with pytest.raises(DemoSeedConfigurationError, match=DEMO_MERCHANT_PIN_VARIABLE) as raised:
        read_demo_merchant_pin(environment)
    for value in environment.values():
        if value:
            assert value not in str(raised.value)


def test_build_demo_merchant_seed_matches_the_design_spec_sample_data() -> None:
    """Ravi Electronics, RAVI-0193, Counter tablet 1 and the three M2 products and prices."""
    demo_merchant = build_demo_merchant_seed(SYNTHETIC_PIN)
    assert (demo_merchant.shop_code, demo_merchant.display_name) == (
        "RAVI-0193",
        "Ravi Electronics",
    )
    assert demo_merchant.counter_device_label == "Counter tablet 1"
    assert [(product.name, product.list_price) for product in demo_merchant.products] == [
        ("Example phone, 128 GB", Money.from_rupees("22000")),
        ("Example phone, 64 GB", Money.from_rupees("18000")),
        ("Example earbuds", Money.from_rupees("2499")),
    ]
    assert {product.gateway_product_id for product in demo_merchant.products} == set(
        MOCK_PLAN_DEFINITIONS_BY_PRODUCT_ID
    )


def test_seed_steps_create_the_shop_before_its_report_history() -> None:
    """The history needs the shop and its products, so it runs second."""
    assert (seed_demo_merchant, seed_report_history) == DEMO_SEED_STEPS


def test_report_history_is_skipped_in_paytm_mode(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The history names the Mock's products, so the real gateway is never asked for them."""
    monkeypatch.setenv("PAYMENT_GATEWAY_MODE", "paytm")

    def refuse_unit_of_work() -> NoReturn:
        """Fails the test if the step opens a transaction."""
        raise AssertionError

    with caplog.at_level(logging.WARNING):
        seed_report_history(refuse_unit_of_work, SYNTHETIC_PIN)
    assert "demo report history skipped" in caplog.text
