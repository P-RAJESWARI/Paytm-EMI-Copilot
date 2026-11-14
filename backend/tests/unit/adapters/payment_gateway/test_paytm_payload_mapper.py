"""paytm_payload_mapper: banks and tenures into offers, ADR 0010 extra cost, whitelisted replies."""

import copy
import logging
from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest

from emi_copilot.adapters.payment_gateway.paytm_payload_mapper import (
    calculate_net_extra_in_total,
    read_bank_card_pairs,
    read_payment_link,
    read_tenure_offers,
)
from emi_copilot.adapters.payment_gateway.paytm_request_builder import BankCardPair
from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiOffer, EmiType
from tests.contract.payment_gateway.paytm_fake_server import load_fixture

LENDER_LABEL = "Demo Bank A"


def load_body(fixture_name: str) -> dict[str, Any]:
    """Gives the body of one fixture, as a fresh copy a test may change."""
    body: dict[str, Any] = load_fixture(fixture_name)["body"]
    return body


def build_plan(**plan_fields: object) -> dict[str, Any]:
    """Builds one SUBVENTION plan on ₹22,000 over 6 months; tests replace single fields."""
    plan: dict[str, Any] = {
        "planId": "SYNTHETIC-PLAN-TEST",
        "emiType": "SUBVENTION",
        "interval": 6,
        "emi": Decimal("3850.00"),
        "interest": Decimal("1100.00"),
    }
    plan.update(plan_fields)
    return plan


def read_single_offer(plan: dict[str, Any]) -> EmiOffer:
    """Reads a Tenures body that holds only this plan and gives its offer."""
    (offer,) = read_tenure_offers({"bankName": LENDER_LABEL, "planDetails": [plan]})
    return offer


def test_read_bank_card_pairs_of_fixture_gives_one_distinct_pair() -> None:
    """The same bank and card under Subvention and Standard is asked about once."""
    assert read_bank_card_pairs(load_body("banks_success.json")) == (
        BankCardPair("DEMOA", "CREDIT_CARD"),
    )


def test_read_bank_card_pairs_keeps_reply_order_across_emi_types() -> None:
    """Each new bank and card type pair is listed once, in the order Paytm sent it."""
    banks_body = load_body("banks_success.json")
    banks_body["emiTypes"][1]["cardTypes"].append({"cardType": "DEBIT_CARD"})
    assert read_bank_card_pairs(banks_body) == (
        BankCardPair("DEMOA", "CREDIT_CARD"),
        BankCardPair("DEMOA", "DEBIT_CARD"),
    )
    assert read_bank_card_pairs({"emiTypes": []}) == ()


@pytest.mark.parametrize(
    "break_banks_body",
    [
        lambda body: body.pop("emiTypes"),
        lambda body: body["emiTypes"][0].update(bankDetails=[{"bankCode": "DEMOA"}]),
        lambda body: body["emiTypes"][0]["bankDetails"].pop("bankCode"),
        lambda body: body["emiTypes"][0]["cardTypes"][0].update(cardType="PREPAID_CARD"),
        lambda body: body["emiTypes"][0].update(cardTypes={"cardType": "CREDIT_CARD"}),
    ],
    ids=["no-emi-types", "bank-list", "no-bank-code", "unknown-card-type", "card-types-object"],
)
def test_read_bank_card_pairs_refuses_unexpected_shapes(
    break_banks_body: Callable[[dict[str, Any]], object],
) -> None:
    """Only the literal documented nesting is read; anything else fails loudly [Verify]."""
    banks_body = load_body("banks_success.json")
    break_banks_body(banks_body)
    with pytest.raises(InvalidPaymentGatewayValueError):
        read_bank_card_pairs(banks_body)


def test_read_tenure_offers_of_fixture_maps_every_plan_with_adr_0010_extra() -> None:
    """Every plan becomes an offer: discount no-cost, cashback net extra, standard extra."""
    assert read_tenure_offers(load_body("tenures_success.json")) == (
        EmiOffer(
            offer_id="SYNTHETIC-PLAN-NO-COST-6M",
            lender_label=LENDER_LABEL,
            emi_type=EmiType.NO_COST,
            tenure_in_months=6,
            quoted_monthly_installment=Money.from_rupees("3666.67"),
            quoted_extra_in_total=Money.from_paise(0),
        ),
        EmiOffer(
            offer_id="SYNTHETIC-PLAN-CASHBACK-12M",
            lender_label=LENDER_LABEL,
            emi_type=EmiType.STANDARD,
            tenure_in_months=12,
            quoted_monthly_installment=Money.from_rupees("2050.00"),
            quoted_extra_in_total=Money.from_rupees("2590.00"),
        ),
        EmiOffer(
            offer_id="SYNTHETIC-PLAN-STANDARD-6M",
            lender_label=LENDER_LABEL,
            emi_type=EmiType.STANDARD,
            tenure_in_months=6,
            quoted_monthly_installment=Money.from_rupees("3850.00"),
            quoted_extra_in_total=Money.from_rupees("1100.00"),
        ),
    )


@pytest.mark.parametrize(
    ("plan_fields", "expected_emi_type", "expected_extra"),
    [
        ({"gratifications": {"value": Decimal("1100"), "type": "DISCOUNT"}}, EmiType.NO_COST, "0"),
        ({"gratifications": {"value": Decimal("1100"), "type": "CASHBACK"}}, EmiType.NO_COST, "0"),
        ({"gratifications": {"value": "1500.00", "type": "DISCOUNT"}}, EmiType.NO_COST, "0"),
        (
            {"gratifications": {"value": Decimal("600"), "type": "DISCOUNT"}},
            EmiType.STANDARD,
            "500",
        ),
        (
            {"gratifications": {"value": Decimal("1099.99"), "type": "CASHBACK"}},
            EmiType.STANDARD,
            "0.01",
        ),
        ({"gratifications": None}, EmiType.STANDARD, "1100"),
        ({}, EmiType.STANDARD, "1100"),
        ({"interest": 0}, EmiType.NO_COST, "0"),
        (
            {
                "emiType": "STANDARD",
                "gratifications": {"value": Decimal("1100"), "type": "DISCOUNT"},
            },
            EmiType.STANDARD,
            "1100",
        ),
    ],
    ids=[
        "discount-equal",
        "cashback-equal",
        "gratification-above-interest-clamps-to-zero",
        "discount-partial",
        "cashback-one-paisa-short",
        "null-gratification",
        "no-gratification",
        "zero-interest",
        "standard-plan-ignores-gratification",
    ],
)
def test_read_tenure_offers_applies_adr_0010_net_extra_and_no_cost_rule(
    plan_fields: dict[str, object], expected_emi_type: EmiType, expected_extra: str
) -> None:
    """Net extra = interest - gratification (never below zero); NO_COST exactly when it is zero."""
    offer = read_single_offer(build_plan(**plan_fields))
    assert offer.emi_type is expected_emi_type
    assert offer.quoted_extra_in_total == Money.from_rupees(expected_extra)
    assert offer.quoted_monthly_installment == Money.from_rupees("3850.00")


def test_read_tenure_offers_keeps_paytm_emi_even_when_it_disagrees_with_the_net_extra() -> None:
    """A big cashback leaves Paytm's gross emi unchanged; the service audits the mismatch."""
    offer = read_single_offer(
        build_plan(gratifications={"value": Decimal("1100"), "type": "CASHBACK"})
    )
    assert offer.emi_type is EmiType.NO_COST
    assert offer.quoted_monthly_installment == Money.from_rupees("3850.00")


def test_calculate_net_extra_in_total_never_goes_below_zero() -> None:
    """The ADR 0010 subtraction stops at zero instead of raising for a negative Money."""
    assert calculate_net_extra_in_total(
        Money.from_rupees("100"), Money.from_rupees("250")
    ) == Money.from_paise(0)
    assert calculate_net_extra_in_total(
        Money.from_rupees("100"), Money.from_rupees("40.50")
    ) == Money.from_rupees("59.50")


@pytest.mark.parametrize(
    "plan_fields",
    [
        {"emiType": "LOW_COST"},
        {"interval": Decimal("6.0")},
        {"interval": "6"},
        {"emi": 3850.0},
        {"emi": Decimal("3850.005")},
        {"interest": None},
        {"planId": ""},
        {"gratifications": {"value": Decimal("1"), "type": "VOUCHER"}},
        {"gratifications": [{"value": Decimal("1"), "type": "DISCOUNT"}]},
        {"gratifications": {"type": "DISCOUNT"}},
        {"emi": 0},
    ],
    ids=[
        "unknown-emi-type",
        "decimal-interval",
        "text-interval",
        "float-emi",
        "sub-paise-emi",
        "no-interest",
        "blank-plan-id",
        "unknown-gratification-type",
        "gratification-list",
        "gratification-without-value",
        "zero-emi",
    ],
)
def test_read_tenure_offers_refuses_malformed_plans(plan_fields: dict[str, object]) -> None:
    """A plan that does not fit the documented shape raises instead of being guessed at."""
    with pytest.raises(InvalidPaymentGatewayValueError):
        read_single_offer(build_plan(**plan_fields))


def test_read_tenure_offers_needs_the_bank_name_and_plan_list() -> None:
    """The lender label is the bank name; without it, or without planDetails, nothing is read."""
    tenures_body = load_body("tenures_success.json")
    without_bank_name = copy.deepcopy(tenures_body)
    without_bank_name.pop("bankName")
    without_plans = copy.deepcopy(tenures_body)
    without_plans.pop("planDetails")
    for unusable_body in (without_bank_name, without_plans):
        with pytest.raises(InvalidPaymentGatewayValueError):
            read_tenure_offers(unusable_body)


def test_read_payment_link_uses_the_short_url_and_text_link_id() -> None:
    """The short URL is the payment URL; the numeric link id becomes text; longUrl is unused."""
    payment_link = read_payment_link(load_body("create_link_success.json"), "ORDER-SAMPLE-0001")
    assert payment_link.order_id == "ORDER-SAMPLE-0001"
    assert payment_link.gateway_link_id == "90000001"
    assert payment_link.payment_url == "https://short-link.example.test/SYNTHLINK0001"


@pytest.mark.parametrize(
    "link_fields",
    [{"shortUrl": "http://short-link.example.test/x"}, {"shortUrl": None}, {"linkId": None}],
)
def test_read_payment_link_refuses_a_missing_or_insecure_link(
    link_fields: dict[str, object],
) -> None:
    """Only a complete https short link can reach the customer."""
    link_body = {**load_body("create_link_success.json"), **link_fields}
    with pytest.raises(InvalidPaymentGatewayValueError):
        read_payment_link(link_body, "ORDER-SAMPLE-0001")


def test_payload_mapper_logs_nothing_while_mapping_offers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Mapping a reply logs no event at all, so no vendor message can reach the logs."""
    with caplog.at_level(logging.DEBUG):
        read_tenure_offers(load_body("tenures_success.json"))
    assert caplog.records == []
