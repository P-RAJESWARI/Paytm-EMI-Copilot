"""PlanAdviceService with the real Layer 1 Mock gateway: C4 order, comfort and C6 alternatives."""

import pytest

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.domain.alternatives import AlternativeKind
from emi_copilot.domain.comfort import ComfortBand, FinancialProfile
from emi_copilot.domain.errors import InvalidMonthlyBudgetError, OfferNotFoundError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import OfferDiscoveryQuery, PricedEmiOffer, price_emi_offer
from emi_copilot.services.plan_advice_service import PlanAdviceService
from emi_copilot.services.plan_advice_types import AlternativesAdvice, CheaperModelCandidate
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT, build_offer_discovery_query

STANDARD_PROFILE = FinancialProfile(Money.from_rupees("30000"), Money.from_rupees("8000"))
RISKY_PROFILE = FinancialProfile(Money.from_rupees("20000"), Money.from_rupees("8000"))
NO_COST_OFFER_ID = "mock-offer-no-cost-6m"
CARD_OFFER_ID = "mock-offer-card-6m"
CARDLESS_OFFER_ID = "mock-offer-cardless-12m"
CHEAPER_MODEL = CheaperModelCandidate(
    product_id="product-sample-64gb",
    product_name="Example phone, 64 GB",
    price=Money.from_rupees("18000"),
    brand_id="brand-sample-0001",
    category_id="category-sample-0001",
)


class MockGatewayOfferSource:
    """Prices the Mock gateway's quotes with the engine and remembers every query it was asked."""

    def __init__(self) -> None:
        """Builds the real Layer 1 Mock gateway on a fixed clock."""
        self._payment_gateway = MockPaymentGatewayAdapter(FixedClock(CREATED_AT), bytes(range(32)))
        self.queries: list[OfferDiscoveryQuery] = []

    def discover_offers(self, query: OfferDiscoveryQuery) -> tuple[PricedEmiOffer, ...]:
        """Gives the Mock's offers for the item, priced on the item's price."""
        self.queries.append(query)
        return tuple(
            price_emi_offer(offer, query.price)
            for offer in self._payment_gateway.discover_offers(query)
        )


@pytest.fixture
def offer_source() -> MockGatewayOfferSource:
    """Gives a fresh offer source over the Mock gateway."""
    return MockGatewayOfferSource()


@pytest.fixture
def service(offer_source: MockGatewayOfferSource) -> PlanAdviceService:
    """Gives the service with every rule at its ADR 0020 default."""
    return PlanAdviceService(offer_source)


def list_offer_ids(service: PlanAdviceService, budget_in_rupees: str) -> list[str]:
    """Ranks the design item for a budget and lists the offer ids in order."""
    comparison = service.compare_plans(
        build_offer_discovery_query(), Money.from_rupees(budget_in_rupees), None
    )
    return [plan.ranked_plan.priced_offer.offer.offer_id for plan in comparison.advised_plans]


def test_compare_plans_three_thousand_budget_gives_design_order_and_amounts_above(
    service: PlanAdviceService,
) -> None:
    """C4: cardless fits, then no-cost ₹666.67 above, then card ₹850 above."""
    comparison = service.compare_plans(
        build_offer_discovery_query(), Money.from_rupees("3000"), None
    )
    assert list_offer_ids(service, "3000") == [CARDLESS_OFFER_ID, NO_COST_OFFER_ID, CARD_OFFER_ID]
    assert [
        plan.ranked_plan.budget_fit.amount_above_budget.to_paise()
        for plan in comparison.advised_plans
    ] == [0, 66_667, 85_000]
    assert comparison.ranking.has_any_plan_within_budget


def test_compare_plans_eighteen_hundred_budget_keeps_every_plan_above_budget(
    service: PlanAdviceService,
) -> None:
    """₹1,800: nothing fits, yet all three plans are listed."""
    comparison = service.compare_plans(
        build_offer_discovery_query(), Money.from_rupees("1800"), None
    )
    assert len(comparison.advised_plans) == 3
    assert not comparison.ranking.has_any_plan_within_budget
    assert list_offer_ids(service, "1800") == [CARDLESS_OFFER_ID, NO_COST_OFFER_ID, CARD_OFFER_ID]


def test_compare_plans_skipped_comfort_check_gives_no_assessment(
    service: PlanAdviceService,
) -> None:
    """Without consent the plans show without bands."""
    comparison = service.compare_plans(
        build_offer_discovery_query(), Money.from_rupees("3000"), None
    )
    assert not comparison.has_comfort_check
    assert all(plan.comfort is None for plan in comparison.advised_plans)


def test_compare_plans_standard_profile_gives_design_ratios(service: PlanAdviceService) -> None:
    """Cardless 33.50% Comfortable, no-cost 38.89% and card 39.50% Stretching."""
    comparison = service.compare_plans(
        build_offer_discovery_query(), Money.from_rupees("3000"), STANDARD_PROFILE
    )
    assessments = [plan.comfort for plan in comparison.advised_plans]
    assert comparison.has_comfort_check
    assert [assessment.total_ratio.in_basis_points for assessment in assessments if assessment] == [
        3350,
        3889,
        3950,
    ]
    assert [assessment.band for assessment in assessments if assessment] == [
        ComfortBand.COMFORTABLE,
        ComfortBand.STRETCHING,
        ComfortBand.STRETCHING,
    ]


def test_compare_plans_risky_profile_gives_plan_b_risky_at_5925(
    service: PlanAdviceService,
) -> None:
    """The design's second customer: plan B is 59.25%, Risky."""
    comparison = service.compare_plans(
        build_offer_discovery_query(), Money.from_rupees("3000"), RISKY_PROFILE
    )
    (card_plan,) = [
        plan
        for plan in comparison.advised_plans
        if plan.ranked_plan.priced_offer.offer.offer_id == CARD_OFFER_ID
    ]
    assert card_plan.comfort is not None
    assert card_plan.comfort.total_ratio.in_basis_points == 5925
    assert card_plan.comfort.band is ComfortBand.RISKY


def suggest_design_alternatives(
    service: PlanAdviceService, financial_profile: FinancialProfile | None = STANDARD_PROFILE
) -> AlternativesAdvice:
    """Asks for C6's alternatives to no-cost 6 months on ₹22,000 with a ₹3,000 budget."""
    return service.suggest_alternatives(
        build_offer_discovery_query(),
        NO_COST_OFFER_ID,
        Money.from_rupees("3000"),
        financial_profile,
        [CHEAPER_MODEL],
    )


def test_suggest_alternatives_design_data_gives_engine_figures(
    service: PlanAdviceService,
) -> None:
    """₹4,000 down gives ₹3,000.00 (36.67%); cardless 33.50%; the 64 GB ₹3,000.00 (36.67%)."""
    advice = suggest_design_alternatives(service)
    alternatives = [advised.alternative for advised in advice.advised_alternatives]
    assert [alternative.kind for alternative in alternatives] == [
        AlternativeKind.DOWN_PAYMENT,
        AlternativeKind.LONGER_TENURE,
        AlternativeKind.CHEAPER_MODEL,
    ]
    assert alternatives[0].down_payment == Money.from_rupees("4000")
    assert [alternative.monthly_commitment.to_paise() for alternative in alternatives] == [
        300_000,
        205_000,
        300_000,
    ]
    assert alternatives[1].priced_offer.offer.offer_id == CARDLESS_OFFER_ID
    assert [
        advised.comfort.total_ratio.in_basis_points
        for advised in advice.advised_alternatives
        if advised.comfort
    ] == [3667, 3350, 3667]
    assert advice.has_lower_monthly_alternative


def test_suggest_alternatives_describes_the_chosen_plan_with_fit_and_comfort(
    service: PlanAdviceService,
) -> None:
    """The base plan is no-cost ₹3,666.67, ₹666.67 above budget, 38.89%."""
    advice = suggest_design_alternatives(service)
    assert advice.chosen_plan.offer.offer_id == NO_COST_OFFER_ID
    assert advice.chosen_plan_budget_fit.amount_above_budget.to_paise() == 66_667
    assert advice.chosen_plan_comfort is not None
    assert advice.chosen_plan_comfort.total_ratio.in_basis_points == 3889


def test_suggest_alternatives_requotes_reduced_price_and_cheaper_model_with_same_ids(
    service: PlanAdviceService, offer_source: MockGatewayOfferSource
) -> None:
    """The item at ₹18,000 keeps its catalogue ids; the 64 GB model is asked by its own ids."""
    suggest_design_alternatives(service)
    item_query = build_offer_discovery_query()
    assert offer_source.queries == [
        item_query,
        OfferDiscoveryQuery(
            price=Money.from_rupees("18000"),
            product_id=item_query.product_id,
            brand_id=item_query.brand_id,
            category_id=item_query.category_id,
        ),
        CHEAPER_MODEL.to_offer_discovery_query(),
    ]


def test_suggest_alternatives_skipped_comfort_and_fitting_plan_asks_no_extra_quotes(
    service: PlanAdviceService, offer_source: MockGatewayOfferSource
) -> None:
    """Chosen cardless fits, so no down payment; a dearer model is not quoted; no comfort."""
    dearer_model = CheaperModelCandidate(
        "product-sample-256gb", "Example phone, 256 GB", Money.from_rupees("26000"), "b", "c"
    )
    advice = service.suggest_alternatives(
        build_offer_discovery_query(),
        CARDLESS_OFFER_ID,
        Money.from_rupees("3000"),
        None,
        [dearer_model],
    )
    assert advice.advised_alternatives == ()
    assert not advice.has_lower_monthly_alternative
    assert advice.chosen_plan_comfort is None
    assert len(offer_source.queries) == 1


def test_suggest_alternatives_unknown_chosen_offer_raises_offer_not_found(
    service: PlanAdviceService,
) -> None:
    """An offer id the gateway does not quote for the item is refused."""
    with pytest.raises(OfferNotFoundError):
        service.suggest_alternatives(
            build_offer_discovery_query(),
            "offer-not-quoted",
            Money.from_rupees("3000"),
            None,
            [],
        )


def test_compare_plans_with_zero_budget_raises_before_asking_the_gateway(
    service: PlanAdviceService, offer_source: MockGatewayOfferSource
) -> None:
    """An invalid budget is refused first, so no quote is requested."""
    with pytest.raises(InvalidMonthlyBudgetError):
        service.compare_plans(build_offer_discovery_query(), Money.from_paise(0), None)
    assert offer_source.queries == []


def test_suggest_alternatives_with_zero_budget_raises_before_asking_the_gateway(
    service: PlanAdviceService, offer_source: MockGatewayOfferSource
) -> None:
    """An invalid budget is refused first, so no quote is requested."""
    with pytest.raises(InvalidMonthlyBudgetError):
        service.suggest_alternatives(
            build_offer_discovery_query(), NO_COST_OFFER_ID, Money.from_paise(0), None, []
        )
    assert offer_source.queries == []
