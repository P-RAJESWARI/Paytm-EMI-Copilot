"""Tests for the EmiOffer value object, which holds a lender's quote as given."""

from dataclasses import fields
from decimal import Decimal

import pytest

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiOffer, EmiType
from tests.payment_builders import build_emi_offer


def test_emi_offer_with_valid_standard_quote_keeps_quoted_amounts() -> None:
    """A standard offer keeps the lender's quoted installment and extra unchanged."""
    emi_offer = build_emi_offer()
    assert emi_offer.quoted_monthly_installment == Money.from_paise(385_000)
    assert emi_offer.quoted_extra_in_total == Money.from_paise(110_000)


def test_emi_offer_no_cost_with_zero_extra_is_valid() -> None:
    """A no-cost offer quoting zero extra is accepted."""
    emi_offer = build_emi_offer(
        emi_type=EmiType.NO_COST,
        quoted_monthly_installment=Money.from_rupees("3666.67"),
        quoted_extra_in_total=Money.from_paise(0),
    )
    assert emi_offer.quoted_extra_in_total.is_zero


def test_emi_offer_standard_with_zero_extra_is_valid() -> None:
    """A standard offer may quote no extra, for example when the lender waives it."""
    assert build_emi_offer(quoted_extra_in_total=Money.from_paise(0)).emi_type is EmiType.STANDARD


def test_emi_offer_no_cost_with_non_zero_extra_raises_invalid_payment_gateway_value_error() -> None:
    """A no-cost offer that quotes an extra cost is inconsistent and rejected."""
    with pytest.raises(InvalidPaymentGatewayValueError, match="no-cost offer quotes no extra"):
        build_emi_offer(emi_type=EmiType.NO_COST)


@pytest.mark.parametrize(
    ("field_overrides", "expected_message"),
    [
        ({"offer_id": ""}, "offer id"),
        ({"lender_label": " "}, "lender label"),
        ({"emi_type": "STANDARD"}, "EmiType"),
        ({"tenure_in_months": 0}, "at least 1 month"),
        ({"tenure_in_months": True}, "whole number"),
        ({"quoted_monthly_installment": Money.from_paise(0)}, "quoted monthly installment"),
        ({"quoted_monthly_installment": Decimal("3850")}, "quoted monthly installment"),
        ({"quoted_extra_in_total": Money.from_rupees("0.001")}, "quoted extra in total"),
    ],
)
def test_emi_offer_with_invalid_field_raises_invalid_payment_gateway_value_error(
    field_overrides: dict[str, object], expected_message: str
) -> None:
    """Blank labels, bad tenures and zero, sub-paise or non-Money amounts are rejected."""
    with pytest.raises(InvalidPaymentGatewayValueError, match=expected_message):
        build_emi_offer(**field_overrides)


def test_emi_offer_is_immutable() -> None:
    """A quote cannot be changed after it is received."""
    emi_offer = build_emi_offer()
    with pytest.raises(AttributeError):
        emi_offer.tenure_in_months = 12  # type: ignore[misc]


def test_emi_offer_holds_no_schedule_fields() -> None:
    """The offer is the quote only; a strategy in the service builds the schedule (ADR 0001)."""
    assert {emi_offer_field.name for emi_offer_field in fields(EmiOffer)} == {
        "offer_id",
        "lender_label",
        "emi_type",
        "tenure_in_months",
        "quoted_monthly_installment",
        "quoted_extra_in_total",
    }
