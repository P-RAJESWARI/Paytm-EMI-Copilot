"""Typed facts an AI text writer may see: the whole contract between prompt builders and writers.

These dataclasses are the only shape of AiTextRequest.structured_facts_json. They hold plan and
report figures and labels only: never a name, phone number, income, existing EMIs, ratio, band,
budget or session id (CLAUDE.md rule 6, plan Q3, ADR 0026). Money is whole rupees as shown.
"""

import json
import re
from dataclasses import asdict, dataclass, fields

_SNAKE_CASE_SEPARATOR = re.compile(r"_([a-z])")


def to_camel_case(field_name: str) -> str:
    """Turns a snake_case field name into the camelCase wire key ("tenure_in_months")."""
    return _SNAKE_CASE_SEPARATOR.sub(lambda match: match.group(1).upper(), field_name)


def _camel_case_keys(value: object) -> object:
    """Renames every dictionary key of a nested structure to camelCase."""
    if isinstance(value, dict):
        return {to_camel_case(key): _camel_case_keys(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_camel_case_keys(item) for item in value]
    return value


def _read_text(value: object) -> str | None:
    """Gives a text value, or None for anything else."""
    return value if isinstance(value, str) else None


def _read_whole_number(value: object) -> int | None:
    """Gives a whole-number value (never a bool), or None for anything else."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


@dataclass(frozen=True, slots=True)
class ExplanationPromptFacts:
    """One chosen plan's shown figures (C7): exactly what the template explanation uses."""

    plan_kind: str
    plan_display_name: str
    lender_label: str
    tenure_in_months: int
    monthly_amount_in_rupees: int
    extra_in_total_in_rupees: int
    total_payable_in_rupees: int
    price_in_rupees: int
    funder_note: str | None

    @classmethod
    def from_json_object(cls, facts_object: dict[str, object]) -> "ExplanationPromptFacts | None":
        """Reads facts written by facts_to_json; None unless exactly these fields, well typed."""
        if set(facts_object) != EXPLANATION_FACT_KEYS:
            return None
        plan_kind, plan_display_name, lender_label = (
            _read_text(facts_object[key]) for key in ("planKind", "planDisplayName", "lenderLabel")
        )
        tenure, monthly, extra, total, price = (
            _read_whole_number(facts_object[key]) for key in EXPLANATION_WHOLE_NUMBER_KEYS
        )
        funder_note = _read_text(facts_object["funderNote"])
        if (
            plan_kind is None
            or plan_display_name is None
            or lender_label is None
            or tenure is None
            or monthly is None
            or extra is None
            or total is None
            or price is None
        ):
            return None
        return cls(
            plan_kind, plan_display_name, lender_label, tenure, monthly, extra, total, price,
            funder_note,
        )  # fmt: skip


@dataclass(frozen=True, slots=True)
class BrandBatchPromptFacts:
    """One expected brand payment: its amount and day."""

    amount_in_rupees: int
    expected_day: str


@dataclass(frozen=True, slots=True)
class SuggestedActionPromptFacts:
    """The first suggested action with its computed figures (M5 "What you can do")."""

    action_code: str
    product_name: str
    tenures_in_months: tuple[int, ...]
    monthly_amounts_in_rupees: tuple[int, ...]
    list_price_in_rupees: int | None


@dataclass(frozen=True, slots=True)
class WeeklyMessagePromptFacts:
    """One week's report figures for the shop; a suppressed count (1 to 4) is None, never sent."""

    period_first_day: str
    period_last_day: str
    customers_started: int | None
    customers_paid: int | None
    biggest_drop_after_stage: str | None
    missed_sales_count: int | None
    missed_sales_monthly_ceiling_in_rupees: int | None
    money_due_from_brands_in_rupees: int
    next_brand_payment_day: str | None
    brand_batches: tuple[BrandBatchPromptFacts, ...]
    suggested_action: SuggestedActionPromptFacts | None


EXPLANATION_FACT_KEYS = frozenset(
    to_camel_case(field.name) for field in fields(ExplanationPromptFacts)
)
EXPLANATION_WHOLE_NUMBER_KEYS = (
    "tenureInMonths",
    "monthlyAmountInRupees",
    "extraInTotalInRupees",
    "totalPayableInRupees",
    "priceInRupees",
)


def facts_to_json(facts: ExplanationPromptFacts | WeeklyMessagePromptFacts) -> str:
    """Serialises facts as camelCase JSON in field order, with Tamil kept readable."""
    return json.dumps(_camel_case_keys(asdict(facts)), ensure_ascii=False)
