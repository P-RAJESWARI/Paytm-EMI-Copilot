"""TeachBackFeedbackWriter: the C8 card in plain words, every plan figure from the engine.

Strings follow docs/design/mockups-source/C8.dc.html (closeTitle, closeBody, extra0, again,
heard). The mockup shows one card, titled "Nearly there", with the correct terms; it adds
"Explain it again" after a TRY_AGAIN. The sentence for a plan with an extra is not in the
mockup and follows its wording.
"""

from dataclasses import dataclass
from types import MappingProxyType

from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.number_audit.allowed_numbers import whole_rupees_of
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.domain.teach_back import TeachBackResult
from emi_copilot.services.customer.explanation_types import RupeeFormatter

_PAISE_PER_RUPEE = 100
# The C8 chip such as "₹3,667 (times) 6"; the multiplication sign is escaped as it looks like x.
MONTHLY_BY_TENURE_TEMPLATE = "{monthly} \u00d7 {tenure}"


@dataclass(frozen=True, slots=True)
class TeachBackWording:
    """One language's C8 strings; {placeholders} take already formatted values."""

    title: str
    body_without_extra: str
    body_with_extra: str
    monthly_by_tenure: str
    extra_label: str
    heard: str
    explain_again: str


TEACH_BACK_WORDING = MappingProxyType(
    {
        CustomerLanguage.ENGLISH: TeachBackWording(
            title="Nearly there",
            body_without_extra=(
                "You will pay {monthly} every month for {tenure} months. "
                "Nothing extra on top of {price}."
            ),
            body_with_extra=(
                "You will pay {monthly} every month for {tenure} months. "
                "{extra} extra on top of {price}."
            ),
            monthly_by_tenure=MONTHLY_BY_TENURE_TEMPLATE,
            extra_label="Extra {extra}",
            heard="About {heard} every month",
            explain_again="Explain it again",
        ),
        # draft: needs native review (every Tamil string below)
        CustomerLanguage.TAMIL: TeachBackWording(
            title="கிட்டத்தட்ட சரி",
            body_without_extra=(
                "நீங்கள் {tenure} மாதங்களுக்கு ஒவ்வொரு மாதமும் {monthly} செலுத்துவீர்கள். "
                "{price}-க்கு மேல் கூடுதல் இல்லை."
            ),
            body_with_extra=(
                "நீங்கள் {tenure} மாதங்களுக்கு ஒவ்வொரு மாதமும் {monthly} செலுத்துவீர்கள். "
                "{price}-க்கு மேல் கூடுதலாக {extra}."
            ),
            monthly_by_tenure=MONTHLY_BY_TENURE_TEMPLATE,
            extra_label="கூடுதல் {extra}",
            heard="மாதம் சுமார் {heard}",
            explain_again="மீண்டும் விளக்கவும்",
        ),
    }
)


@dataclass(frozen=True, slots=True)
class TeachBackFeedback:
    """The advisory C8 card; nothing about it is stored."""

    result: TeachBackResult
    title: str
    body: str
    highlighted_terms: tuple[str, ...]
    heard_text: str | None
    explain_again_label: str | None


def find_heard_monthly_amount(stated_numbers: tuple[int, ...], plan: ChosenPlan) -> int | None:
    """Gives the number said closest to the monthly amount, ignoring the tenure; None if none."""
    monthly_in_rupees = whole_rupees_of(plan.monthly_installment)
    candidates = [number for number in stated_numbers if number != plan.tenure_in_months]
    if not candidates:
        return None
    return min(candidates, key=lambda number: abs(number - monthly_in_rupees))


class TeachBackFeedbackWriter:
    """Writes the C8 card from the engine's figures; only "heard" echoes the customer's number."""

    def __init__(self, rupee_formatter: RupeeFormatter) -> None:
        """Keeps the one backend formatter of rupee amounts in sent text (ADR 0018)."""
        self._rupee_formatter = rupee_formatter

    def write(
        self,
        plan: ChosenPlan,
        language: CustomerLanguage,
        result: TeachBackResult,
        stated_numbers: tuple[int, ...],
    ) -> TeachBackFeedback:
        """Restates the plan's terms; after TRY_AGAIN it offers to explain the plan again."""
        wording = TEACH_BACK_WORDING[language]
        monthly = self._rupee_formatter(plan.monthly_installment.to_paise())
        extra = self._rupee_formatter(plan.extra_in_total.to_paise())
        return TeachBackFeedback(
            result=result,
            title=wording.title,
            body=self._write_body(plan, wording, monthly, extra),
            highlighted_terms=(
                wording.monthly_by_tenure.format(monthly=monthly, tenure=plan.tenure_in_months),
                wording.extra_label.format(extra=extra),
            ),
            heard_text=self._write_heard(plan, wording, stated_numbers),
            explain_again_label=(
                wording.explain_again if result is TeachBackResult.TRY_AGAIN else None
            ),
        )

    def _write_body(
        self, plan: ChosenPlan, wording: TeachBackWording, monthly: str, extra: str
    ) -> str:
        """Gives closeBody: the monthly, the tenure, and the extra (or nothing) on the price."""
        body = (
            wording.body_without_extra if plan.extra_in_total.is_zero else wording.body_with_extra
        )
        return body.format(
            monthly=monthly,
            tenure=plan.tenure_in_months,
            extra=extra,
            price=self._rupee_formatter(plan.price.to_paise()),
        )

    def _write_heard(
        self, plan: ChosenPlan, wording: TeachBackWording, stated_numbers: tuple[int, ...]
    ) -> str | None:
        """Gives "About ₹X every month" for the amount heard; None when no amount was said."""
        heard_amount = find_heard_monthly_amount(stated_numbers, plan)
        if heard_amount is None:
            return None
        return wording.heard.format(heard=self._rupee_formatter(heard_amount * _PAISE_PER_RUPEE))
