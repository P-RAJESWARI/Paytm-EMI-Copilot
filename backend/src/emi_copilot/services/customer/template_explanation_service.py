"""TemplateExplanationService: the standard plain-words explanation of one plan (C7)."""

from dataclasses import dataclass
from types import MappingProxyType

from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.services.customer.explanation_types import (
    ExplanationSource,
    ExplanationText,
    HighlightedAmount,
    HighlightedAmountKind,
    RupeeFormatter,
)


@dataclass(frozen=True, slots=True)
class ExplanationWording:
    """One language's sentences; {monthly}, {tenure} and {extra} are filled from the plan."""

    plan_names_by_kind: MappingProxyType[EmiType, str]
    monthly_sentence: str
    extra_sentence: str
    no_extra_sentence: str


ENGLISH_WORDING = ExplanationWording(
    plan_names_by_kind=MappingProxyType({EmiType.NO_COST: "No-cost EMI", EmiType.STANDARD: "EMI"}),
    monthly_sentence="{plan_name}: you pay {monthly} each month for {tenure} months.",
    extra_sentence="The extra you pay in total is {extra}, on top of the price.",
    no_extra_sentence="The extra you pay in total is {extra}, so nothing is added to the price.",
)

# draft: needs native review (every Tamil sentence below)
TAMIL_WORDING = ExplanationWording(
    plan_names_by_kind=MappingProxyType({EmiType.NO_COST: "கட்டணமில்லா EMI", EmiType.STANDARD: "EMI"}),
    monthly_sentence="{plan_name}: ஒவ்வொரு மாதமும் {monthly}, {tenure} மாதங்களுக்குச் செலுத்துவீர்கள்.",
    extra_sentence="மொத்தத்தில் நீங்கள் கூடுதலாகச் செலுத்துவது {extra}, விலைக்கு மேல்.",
    no_extra_sentence="மொத்தத்தில் நீங்கள் கூடுதலாகச் செலுத்துவது {extra}; விலைக்கு மேல் எதுவும் இல்லை.",
)

WORDING_BY_LANGUAGE = MappingProxyType(
    {CustomerLanguage.ENGLISH: ENGLISH_WORDING, CustomerLanguage.TAMIL: TAMIL_WORDING}
)


# Pattern: Template fallback (Null Object flavour). Always gives a safe explanation built only
# from engine figures; Layer 4's audited AI explainer wraps it and falls back to it.
class TemplateExplanationService:
    """Explains a plan in plain words from its figures alone; it never fails and never guesses.

    It says "extra you pay", never an interest rate, and nothing is called best or urgent. The
    rupee amounts in the text are exactly the highlighted amounts, formatted as whole rupees
    rounded half-up, like the customer app's formatRupeesFromPaise.
    """

    def __init__(self, rupee_formatter: RupeeFormatter) -> None:
        """Keeps the one backend formatter of rupee amounts in sent text (ADR 0018)."""
        self._rupee_formatter = rupee_formatter

    def explain(self, plan: ChosenPlan, language: CustomerLanguage) -> ExplanationText:
        """Gives the template text for the plan in English or (draft) Tamil."""
        wording = WORDING_BY_LANGUAGE[language]
        extra_template = (
            wording.no_extra_sentence if plan.extra_in_total.is_zero else wording.extra_sentence
        )
        monthly_text = self._rupee_formatter(plan.monthly_installment.to_paise())
        extra_text = self._rupee_formatter(plan.extra_in_total.to_paise())
        text = " ".join(
            (
                wording.monthly_sentence.format(
                    plan_name=wording.plan_names_by_kind[plan.plan_kind],
                    monthly=monthly_text,
                    tenure=plan.tenure_in_months,
                ),
                extra_template.format(extra=extra_text),
            )
        )
        return ExplanationText(
            text=text,
            language=language,
            source=ExplanationSource.TEMPLATE,
            highlighted_amounts=(
                HighlightedAmount(
                    HighlightedAmountKind.MONTHLY_INSTALLMENT, plan.monthly_installment
                ),
                HighlightedAmount(HighlightedAmountKind.EXTRA_IN_TOTAL, plan.extra_in_total),
            ),
        )
