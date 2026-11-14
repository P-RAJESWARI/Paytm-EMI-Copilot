"""StubCustomerAdviceService: comfort check consent, plan comparison and alternatives."""

import pytest

from emi_copilot.domain.alternatives import AlternativeKind
from emi_copilot.domain.comfort import ComfortBand
from emi_copilot.domain.errors import BudgetNotConfirmedError, OfferNotFoundError
from emi_copilot.domain.money import Money
from emi_copilot.services.customer_flow.customer_flow_types import ComfortCheckStatus
from tests.unit.services.customer_flow.conftest import CustomerFlowKit


def test_run_comfort_check_before_a_budget_raises(kit: CustomerFlowKit) -> None:
    """C3 comes after the budget is confirmed."""
    credentials = kit.start_standard_session()
    with pytest.raises(BudgetNotConfirmedError):
        kit.services.advice_service.run_comfort_check(credentials, has_customer_consented=True)
    assert kit.profile_port.read_count == 0


def test_run_comfort_check_with_consent_reads_the_synthetic_profile(kit: CustomerFlowKit) -> None:
    """With consent the profile is read once: inflow ₹30,000, existing EMIs ₹8,000."""
    credentials = kit.start_standard_session()
    kit.confirm_budget(credentials)
    outcome = kit.services.advice_service.run_comfort_check(
        credentials, has_customer_consented=True
    )
    assert outcome.status is ComfortCheckStatus.COMPLETED
    assert outcome.is_synthetic_data
    assert outcome.financial_profile is not None
    assert outcome.financial_profile.monthly_inflow == Money.from_rupees("30000")
    assert kit.profile_port.read_count == 1


def test_skipped_comfort_check_never_reads_the_profile_and_plans_show_no_bands(
    kit: CustomerFlowKit,
) -> None:
    """Skipping records the choice; nothing is read, then or for plans and alternatives."""
    credentials = kit.start_standard_session()
    kit.confirm_budget(credentials)
    outcome = kit.services.advice_service.run_comfort_check(
        credentials, has_customer_consented=False
    )
    comparison = kit.services.advice_service.compare_plans(credentials)
    advice = kit.services.advice_service.suggest_alternatives(credentials, "mock-offer-no-cost-6m")
    assert outcome.status is ComfortCheckStatus.SKIPPED
    assert outcome.financial_profile is None
    assert not comparison.has_comfort_check
    assert all(plan.comfort is None for plan in comparison.advised_plans)
    assert advice.chosen_plan_comfort is None
    assert kit.profile_port.read_count == 0


def test_compare_plans_before_a_budget_raises(kit: CustomerFlowKit) -> None:
    """C4 needs the confirmed budget."""
    credentials = kit.start_standard_session()
    with pytest.raises(BudgetNotConfirmedError):
        kit.services.advice_service.compare_plans(credentials)


def test_compare_plans_without_answering_comfort_check_shows_no_bands(
    kit: CustomerFlowKit,
) -> None:
    """Until the customer consents, no profile is read."""
    credentials = kit.start_standard_session()
    kit.confirm_budget(credentials)
    comparison = kit.services.advice_service.compare_plans(credentials)
    assert not comparison.has_comfort_check
    assert kit.profile_port.read_count == 0


def test_compare_plans_with_consent_gives_design_order_and_ratios(kit: CustomerFlowKit) -> None:
    """₹3,000: cardless 3,350, no-cost 3,889, card 3,950 basis points."""
    credentials = kit.start_standard_session()
    kit.confirm_budget(credentials)
    kit.services.advice_service.run_comfort_check(credentials, has_customer_consented=True)
    comparison = kit.services.advice_service.compare_plans(credentials)
    assert [
        (plan.ranked_plan.priced_offer.offer.offer_id, plan.comfort.total_ratio.in_basis_points)
        for plan in comparison.advised_plans
        if plan.comfort
    ] == [
        ("mock-offer-cardless-12m", 3350),
        ("mock-offer-no-cost-6m", 3889),
        ("mock-offer-card-6m", 3950),
    ]


def test_compare_plans_risky_session_gives_plan_b_risky(kit: CustomerFlowKit) -> None:
    """The second sample customer sees plan B at 59.25%, Risky."""
    credentials = kit.start_risky_session()
    kit.confirm_budget(credentials)
    kit.services.advice_service.run_comfort_check(credentials, has_customer_consented=True)
    comparison = kit.services.advice_service.compare_plans(credentials)
    (card_plan,) = [
        plan
        for plan in comparison.advised_plans
        if plan.ranked_plan.priced_offer.offer.offer_id == "mock-offer-card-6m"
    ]
    assert card_plan.comfort is not None
    assert card_plan.comfort.total_ratio.in_basis_points == 5925
    assert card_plan.comfort.band is ComfortBand.RISKY


def test_suggest_alternatives_offers_down_payment_longer_tenure_and_the_64_gb_model(
    kit: CustomerFlowKit,
) -> None:
    """₹4,000 down and the 64 GB phone both give ₹3,000.00 a month; cardless ₹2,050."""
    credentials = kit.start_standard_session()
    kit.confirm_budget(credentials)
    advice = kit.services.advice_service.suggest_alternatives(credentials, "mock-offer-no-cost-6m")
    alternatives = [advised.alternative for advised in advice.advised_alternatives]
    assert [alternative.kind for alternative in alternatives] == [
        AlternativeKind.DOWN_PAYMENT,
        AlternativeKind.LONGER_TENURE,
        AlternativeKind.CHEAPER_MODEL,
    ]
    assert [alternative.monthly_commitment.to_paise() for alternative in alternatives] == [
        300_000,
        205_000,
        300_000,
    ]
    assert alternatives[2].product_name == "Example phone, 64 GB"


def test_suggest_alternatives_unknown_offer_raises(kit: CustomerFlowKit) -> None:
    """An offer the gateway does not quote is not found."""
    credentials = kit.start_standard_session()
    kit.confirm_budget(credentials)
    with pytest.raises(OfferNotFoundError):
        kit.services.advice_service.suggest_alternatives(credentials, "offer-not-quoted")
