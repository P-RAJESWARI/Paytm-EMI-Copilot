"""TemplateExplanationService and CustomerExplanationService: plain words, engine numbers only."""

import re

import pytest

from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.errors import OfferNotFoundError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.customer.explanation_types import (
    ExplanationSource,
    ExplanationText,
    HighlightedAmount,
    HighlightedAmountKind,
)
from emi_copilot.services.customer.template_explanation_service import (
    TemplateExplanationService,
)
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.customer.customer_service_wiring import (
    CustomerServices,
    credentials_of,
    sign_qr_token,
    store_design_shop,
    wire_customer_services,
)

RUPEE_AMOUNT_PATTERN = re.compile(r"₹[0-9]+(?:,[0-9]+)*")
BANNED_WORDS = ("interest", "best", "approved", "declined", "rejected", "eligible", "hurry")
TEMPLATE = TemplateExplanationService(format_paise_as_whole_rupees)


def build_design_plan(offer_letter: str) -> ChosenPlan:
    """Design plans A, B and C on ₹22,000, as quoted."""
    figures = {
        "A": (EmiType.NO_COST, 6, "3666.67", "0", "22000"),
        "B": (EmiType.STANDARD, 6, "3850", "1100", "23100"),
        "C": (EmiType.STANDARD, 12, "2050", "2600", "24600"),
    }[offer_letter]
    plan_kind, tenure, monthly, extra, total = figures
    return ChosenPlan(
        offer_id=f"offer-plan-{offer_letter.lower()}",
        plan_kind=plan_kind,
        lender_label="Synthetic lender",
        tenure_in_months=tenure,
        monthly_installment=Money.from_rupees(monthly),
        extra_in_total=Money.from_rupees(extra),
        total_payable=Money.from_rupees(total),
    )


def rupee_amounts_in(explanation: ExplanationText) -> list[str]:
    """Lists the rupee amounts written in the text, in order."""
    return RUPEE_AMOUNT_PATTERN.findall(explanation.text)


def test_explain_plan_a_in_english_says_nothing_is_added() -> None:
    """Plan A: ₹3,667 a month for 6 months and ₹0 extra, in plain words."""
    explanation = TEMPLATE.explain(build_design_plan("A"), CustomerLanguage.ENGLISH)
    assert explanation.text == (
        "No-cost EMI: you pay ₹3,667 each month for 6 months. "
        "The extra you pay in total is ₹0, so nothing is added to the price."
    )
    assert explanation.source is ExplanationSource.TEMPLATE
    assert explanation.language is CustomerLanguage.ENGLISH
    assert explanation.highlighted_amounts == (
        HighlightedAmount(HighlightedAmountKind.MONTHLY_INSTALLMENT, Money.from_rupees("3666.67")),
        HighlightedAmount(HighlightedAmountKind.EXTRA_IN_TOTAL, Money.from_paise(0)),
    )


def test_explain_plan_c_in_english_names_the_extra_on_top_of_the_price() -> None:
    """Plan C: ₹2,050 a month for 12 months and ₹2,600 extra."""
    explanation = TEMPLATE.explain(build_design_plan("C"), CustomerLanguage.ENGLISH)
    assert explanation.text == (
        "EMI: you pay ₹2,050 each month for 12 months. "
        "The extra you pay in total is ₹2,600, on top of the price."
    )


@pytest.mark.parametrize("offer_letter", ["A", "B", "C"])
@pytest.mark.parametrize("language", list(CustomerLanguage))
def test_explain_writes_exactly_the_highlighted_amounts_and_no_banned_words(
    offer_letter: str, language: CustomerLanguage
) -> None:
    """Every rupee amount in the text is a highlight, rounded half-up as the app shows it."""
    explanation = TEMPLATE.explain(build_design_plan(offer_letter), language)
    assert rupee_amounts_in(explanation) == [
        format_paise_as_whole_rupees(highlight.amount.to_paise())
        for highlight in explanation.highlighted_amounts
    ]
    assert not any(word in explanation.text.lower() for word in BANNED_WORDS)
    assert explanation.language is language


def test_explain_in_tamil_uses_the_draft_tamil_sentences() -> None:
    """The Tamil text is a draft for native review; its numbers are the same figures."""
    explanation = TEMPLATE.explain(build_design_plan("B"), CustomerLanguage.TAMIL)
    assert explanation.text.startswith("EMI: ஒவ்வொரு மாதமும் ₹3,850, 6 மாதங்களுக்கு")
    assert rupee_amounts_in(explanation) == ["₹3,850", "₹1,100"]


@pytest.fixture
def services(kit: ServiceTestKit) -> CustomerServices:
    """Stores the design shop and its CHOOSING sale, then wires the customer services."""
    store_design_shop(kit)
    return wire_customer_services(kit)


@pytest.fixture
def credentials(services: CustomerServices) -> CustomerSessionCredentials:
    """Exchanges the sale's QR for a session."""
    return credentials_of(services.sessions.start(sign_qr_token(services.qr_token_signer)))


def test_explain_for_session_uses_the_fresh_quote_of_the_sessions_item(
    services: CustomerServices, credentials: CustomerSessionCredentials
) -> None:
    """The Mock's card plan on ₹22,000 is explained with its quoted figures."""
    explanation = services.explanation.explain_for_session(
        credentials, "mock-offer-card-6m", CustomerLanguage.ENGLISH
    )
    assert rupee_amounts_in(explanation) == ["₹3,850", "₹1,100"]


def test_explain_for_session_of_an_offer_not_quoted_is_not_found(
    services: CustomerServices, credentials: CustomerSessionCredentials
) -> None:
    """An offer the item is not quoted with cannot be explained."""
    with pytest.raises(OfferNotFoundError):
        services.explanation.explain_for_session(
            credentials, "offer-for-another-product", CustomerLanguage.ENGLISH
        )
