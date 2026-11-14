"""Tests for PlanAlternativeFinder with the design data (C6, ADR 0020 decisions 1 and 2)."""

import pytest

from emi_copilot.domain.alternatives import (
    AlternativeKind,
    CheaperModelQuote,
    DownPaymentRule,
    PlanAlternativeFinder,
    PlanAlternatives,
)
from emi_copilot.domain.comfort import (
    ComfortBandClassificationStrategy,
    FinancialProfile,
    assess_comfort,
)
from emi_copilot.domain.errors import InvalidEmiTermsError, InvalidMonthlyBudgetError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer
from tests.plan_builders import (
    CARDLESS_OFFER_ID,
    CHEAPER_MODEL_PRICE,
    NO_COST_OFFER_ID,
    SAMPLE_PRICE,
    build_card_plan_b,
    build_cardless_plan_c,
    build_design_plans,
    build_no_cost_plan_a,
    build_priced_plan,
)

THREE_THOUSAND_RUPEES = Money.from_rupees("3000")
STANDARD_PROFILE = FinancialProfile(Money.from_rupees("30000"), Money.from_rupees("8000"))
ZERO_RUPEES = Money.from_paise(0)


def build_cheaper_model(
    priced_offers: tuple[PricedEmiOffer, ...] | None = None,
    price: Money = CHEAPER_MODEL_PRICE,
) -> CheaperModelQuote:
    """Builds the design's 64 GB model at ₹18,000, by default with no-cost 6 months only."""
    if priced_offers is None:
        priced_offers = (build_no_cost_plan_a(price),)
    return CheaperModelQuote(
        product_id="product-sample-64gb",
        product_name="Example phone, 64 GB",
        price=price,
        priced_offers=priced_offers,
    )


def find_design_alternatives() -> PlanAlternatives:
    """Finds C6's alternatives for no-cost 6 months on ₹22,000 with a ₹3,000 budget."""
    chosen_plan = build_no_cost_plan_a()
    down_payment = DownPaymentRule().suggest_down_payment(chosen_plan, THREE_THOUSAND_RUPEES)
    assert down_payment is not None
    return PlanAlternativeFinder().find_alternatives(
        chosen_plan,
        item_offers=build_design_plans(),
        monthly_budget=THREE_THOUSAND_RUPEES,
        down_payment=down_payment,
        down_payment_offers=(build_no_cost_plan_a(SAMPLE_PRICE - down_payment),),
        cheaper_models=(build_cheaper_model(),),
    )


def test_find_alternatives_design_data_gives_three_kinds_in_c6_order() -> None:
    """Down payment, then cardless 12 months, then the 64 GB model; all lower than ₹3,666.67."""
    plan_alternatives = find_design_alternatives()

    assert [alternative.kind for alternative in plan_alternatives.alternatives] == [
        AlternativeKind.DOWN_PAYMENT,
        AlternativeKind.LONGER_TENURE,
        AlternativeKind.CHEAPER_MODEL,
    ]
    assert plan_alternatives.chosen_plan == build_no_cost_plan_a()
    assert all(
        alternative.previous_monthly_commitment.to_paise() == 366_667
        and alternative.is_lower_monthly_amount
        for alternative in plan_alternatives.alternatives
    )
    assert plan_alternatives.has_lower_monthly_alternative


def test_find_alternatives_design_down_payment_is_four_thousand_giving_three_thousand() -> None:
    """₹4,000 down leaves ₹18,000 no-cost: exactly ₹3,000.00 x 6, nothing extra (not ₹2,999)."""
    down_payment_alternative = find_design_alternatives().alternatives[0]
    schedule = down_payment_alternative.priced_offer.schedule

    assert down_payment_alternative.down_payment == Money.from_rupees("4000")
    assert down_payment_alternative.priced_offer.offer.offer_id == NO_COST_OFFER_ID
    assert schedule.regular_installment.to_paise() == 300_000
    assert schedule.last_installment.to_paise() == 300_000
    assert schedule.extra_in_total.is_zero
    assert down_payment_alternative.budget_fit.is_within_budget
    assert down_payment_alternative.product_id is None


def test_find_alternatives_design_longer_tenure_is_cardless_twelve_months() -> None:
    """The only longer plan is cardless: ₹2,050 x 12 with ₹2,600 extra in total."""
    longer_alternative = find_design_alternatives().alternatives[1]
    schedule = longer_alternative.priced_offer.schedule

    assert longer_alternative.priced_offer.offer.offer_id == CARDLESS_OFFER_ID
    assert schedule.tenure_in_months == 12
    assert longer_alternative.monthly_commitment == Money.from_rupees("2050")
    assert schedule.extra_in_total == Money.from_rupees("2600")
    assert longer_alternative.down_payment.is_zero


def test_find_alternatives_design_cheaper_model_is_three_thousand_no_cost() -> None:
    """The 64 GB model at ₹18,000 on the same no-cost offer is ₹3,000.00 a month."""
    cheaper_alternative = find_design_alternatives().alternatives[2]

    assert cheaper_alternative.product_id == "product-sample-64gb"
    assert cheaper_alternative.product_name == "Example phone, 64 GB"
    assert cheaper_alternative.priced_offer.offer.offer_id == NO_COST_OFFER_ID
    assert cheaper_alternative.monthly_commitment.to_paise() == 300_000


def test_find_alternatives_design_comfort_ratios_are_engine_figures() -> None:
    """With the standard profile: down payment 36.67%, cardless 33.50%, cheaper model 36.67%."""
    strategy = ComfortBandClassificationStrategy()
    total_ratios_in_basis_points = [
        assess_comfort(
            STANDARD_PROFILE, alternative.monthly_commitment, strategy
        ).total_ratio.in_basis_points
        for alternative in find_design_alternatives().alternatives
    ]
    assert total_ratios_in_basis_points == [3667, 3350, 3667]


def test_find_alternatives_lowest_monthly_plan_alone_has_nothing_better() -> None:
    """Chosen cardless with no down payment and no cheaper model: the C6 "nothing better" state."""
    plan_alternatives = PlanAlternativeFinder().find_alternatives(
        build_cardless_plan_c(),
        item_offers=build_design_plans(),
        monthly_budget=THREE_THOUSAND_RUPEES,
        down_payment=None,
        down_payment_offers=(),
        cheaper_models=(),
    )
    assert plan_alternatives.alternatives == ()
    assert not plan_alternatives.has_lower_monthly_alternative


def test_find_alternatives_keeps_an_option_that_does_not_lower_the_monthly_amount() -> None:
    """A cheaper model at ₹3,000 a month is shown to a cardless customer, marked not lower."""
    plan_alternatives = PlanAlternativeFinder().find_alternatives(
        build_cardless_plan_c(),
        item_offers=build_design_plans(),
        monthly_budget=THREE_THOUSAND_RUPEES,
        down_payment=None,
        down_payment_offers=(),
        cheaper_models=(build_cheaper_model(),),
    )
    (cheaper_alternative,) = plan_alternatives.alternatives
    assert not cheaper_alternative.is_lower_monthly_amount
    assert not plan_alternatives.has_lower_monthly_alternative


def test_find_alternatives_cheaper_model_lacking_chosen_offer_uses_lowest_monthly() -> None:
    """Without the chosen offer id, the model's lowest monthly plan is used; ties go by offer id."""
    model_offers = (
        build_priced_plan("offer-z-12m", 12, ZERO_RUPEES, CHEAPER_MODEL_PRICE),
        build_priced_plan("offer-y-6m", 6, ZERO_RUPEES, CHEAPER_MODEL_PRICE),
        build_priced_plan("offer-x-12m", 12, ZERO_RUPEES, CHEAPER_MODEL_PRICE),
    )
    plan_alternatives = PlanAlternativeFinder().find_alternatives(
        build_card_plan_b(),
        item_offers=(),
        monthly_budget=THREE_THOUSAND_RUPEES,
        down_payment=None,
        down_payment_offers=(),
        cheaper_models=(build_cheaper_model(model_offers),),
    )
    (cheaper_alternative,) = plan_alternatives.alternatives
    assert cheaper_alternative.priced_offer.offer.offer_id == "offer-x-12m"
    assert cheaper_alternative.monthly_commitment == Money.from_rupees("1500")


def test_find_alternatives_skips_models_not_cheaper_or_without_plans() -> None:
    """A model at the same price or with no quoted plan gives no alternative."""
    same_price_model = build_cheaper_model((build_no_cost_plan_a(),), price=SAMPLE_PRICE)
    model_without_plans = build_cheaper_model(())
    plan_alternatives = PlanAlternativeFinder().find_alternatives(
        build_no_cost_plan_a(),
        item_offers=(),
        monthly_budget=THREE_THOUSAND_RUPEES,
        down_payment=None,
        down_payment_offers=(),
        cheaper_models=(same_price_model, model_without_plans),
    )
    assert plan_alternatives.alternatives == ()


def test_find_alternatives_down_payment_offer_not_quoted_gives_no_down_payment_option() -> None:
    """If the chosen offer is not quoted on the reduced price, there is no down-payment option."""
    plan_alternatives = PlanAlternativeFinder().find_alternatives(
        build_no_cost_plan_a(),
        item_offers=(),
        monthly_budget=THREE_THOUSAND_RUPEES,
        down_payment=Money.from_rupees("4000"),
        down_payment_offers=(
            build_priced_plan("offer-other", 6, ZERO_RUPEES, CHEAPER_MODEL_PRICE),
        ),
        cheaper_models=(),
    )
    assert plan_alternatives.alternatives == ()


@pytest.mark.parametrize(
    ("down_payment", "expected_message"),
    [
        (Money.from_rupees("3000"), "price less the down payment"),
        (Money.from_paise(0), "down payment"),
    ],
)
def test_find_alternatives_with_an_inconsistent_down_payment_raises(
    down_payment: Money, expected_message: str
) -> None:
    """A zero down payment, or a plan not priced on price less the down payment, is refused."""
    with pytest.raises(InvalidEmiTermsError, match=expected_message):
        PlanAlternativeFinder().find_alternatives(
            build_no_cost_plan_a(),
            item_offers=(),
            monthly_budget=THREE_THOUSAND_RUPEES,
            down_payment=down_payment,
            down_payment_offers=(build_no_cost_plan_a(CHEAPER_MODEL_PRICE),),
            cheaper_models=(),
        )


def test_find_alternatives_with_an_invalid_budget_raises() -> None:
    """A zero budget is refused even when no alternative would be found."""
    with pytest.raises(InvalidMonthlyBudgetError):
        PlanAlternativeFinder().find_alternatives(
            build_no_cost_plan_a(),
            item_offers=(),
            monthly_budget=ZERO_RUPEES,
            down_payment=None,
            down_payment_offers=(),
            cheaper_models=(),
        )


@pytest.mark.parametrize(
    ("product_id", "product_name", "price", "priced_offers", "expected_message"),
    [
        ("", "Example phone, 64 GB", CHEAPER_MODEL_PRICE, (), "product id"),
        ("product-sample-64gb", " ", CHEAPER_MODEL_PRICE, (), "product name"),
        ("product-sample-64gb", "Example phone, 64 GB", ZERO_RUPEES, (), "model price"),
        (
            "product-sample-64gb",
            "Example phone, 64 GB",
            CHEAPER_MODEL_PRICE,
            (build_no_cost_plan_a(),),
            "priced on its price",
        ),
    ],
)
def test_cheaper_model_quote_with_invalid_fields_raises(
    product_id: str,
    product_name: str,
    price: Money,
    priced_offers: tuple[PricedEmiOffer, ...],
    expected_message: str,
) -> None:
    """Blank names, a zero price and plans priced on another amount are refused."""
    with pytest.raises(InvalidEmiTermsError, match=expected_message):
        CheaperModelQuote(product_id, product_name, price, priced_offers)
