"""ChosenPlan value object: the plan a customer agreed to, frozen exactly as it was shown."""

from collections.abc import Mapping
from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidSaleDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType, PricedEmiOffer
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_positive_whole_paise_money,
    require_tenure_in_months,
    require_whole_paise_money,
)

ChosenPlanDictionary = dict[str, str | int]
"""The JSON-compatible stored form: text fields and integer paise, never floats."""

_TEXT_KEYS = ("offer_id", "plan_kind", "lender_label")
_INTEGER_KEYS = (
    "tenure_in_months",
    "monthly_installment_in_paise",
    "extra_in_total_in_paise",
    "total_payable_in_paise",
)
_ALL_KEYS = frozenset(_TEXT_KEYS + _INTEGER_KEYS)


def _read_stored_value[ValueType](
    stored_plan: Mapping[str, object], key: str, value_type: type[ValueType]
) -> ValueType:
    """Reads one stored field of the expected type; bools never pass as integers."""
    value = stored_plan[key]
    if isinstance(value, bool) or not isinstance(value, value_type):
        raise InvalidSaleDataError(f"The stored chosen plan field {key!r} has the wrong type.")
    return value


def _read_plan_kind(stored_plan: Mapping[str, object]) -> EmiType:
    """Reads the plan kind by its stored value, rejecting values this code does not know."""
    plan_kind_value = _read_stored_value(stored_plan, "plan_kind", str)
    try:
        return EmiType(plan_kind_value)
    except ValueError as unknown_value_error:
        raise InvalidSaleDataError(
            f"The stored plan kind {plan_kind_value!r} is not a known EmiType."
        ) from unknown_value_error


def _read_paise(stored_plan: Mapping[str, object], key: str) -> Money:
    """Reads one stored integer paise field as Money; Money itself refuses negatives."""
    return Money.from_paise(_read_stored_value(stored_plan, key, int))


# Pattern: Value Object. Frozen evidence of the agreed plan, so the merchant's view and the later
# payment hand-off show exactly the figures the customer agreed to.
@dataclass(frozen=True, slots=True)
class ChosenPlan:
    """The agreed plan: the lender's quoted monthly figure (ADR 0001), the extra and the total.

    monthly_installment is what the customer was shown each month, which is the lender's quote,
    not our schedule's regular installment. extra_in_total and total_payable come from our exact
    schedule on the sale price, so total_payable minus extra_in_total is always the price. It
    holds no card or personal data.
    """

    offer_id: str
    plan_kind: EmiType
    lender_label: str
    tenure_in_months: int
    monthly_installment: Money
    extra_in_total: Money
    total_payable: Money

    def __post_init__(self) -> None:
        """Rejects blank labels, a bad tenure, sub-paise amounts and inconsistent totals."""
        require_non_empty_text(self.offer_id, "offer id", InvalidSaleDataError)
        require_non_empty_text(self.lender_label, "lender label", InvalidSaleDataError)
        if not isinstance(self.plan_kind, EmiType):
            raise InvalidSaleDataError("The plan kind must be an EmiType.")
        require_tenure_in_months(self.tenure_in_months, "tenure", InvalidSaleDataError)
        require_positive_whole_paise_money(
            self.monthly_installment, "monthly installment", InvalidSaleDataError
        )
        require_whole_paise_money(self.extra_in_total, "extra in total", InvalidSaleDataError)
        require_positive_whole_paise_money(
            self.total_payable, "total payable", InvalidSaleDataError
        )
        if self.extra_in_total >= self.total_payable:
            raise InvalidSaleDataError("The extra in total must be below the total payable.")
        if self.plan_kind is EmiType.NO_COST and not self.extra_in_total.is_zero:
            raise InvalidSaleDataError("A no-cost plan has no extra in total.")

    @property
    def price(self) -> Money:
        """Gives the item price the plan was quoted on: the total minus the extra."""
        return self.total_payable - self.extra_in_total

    @classmethod
    def from_priced_offer(cls, priced_offer: PricedEmiOffer) -> "ChosenPlan":
        """Freezes a priced offer as shown: the lender's monthly figure and our exact totals."""
        return cls(
            offer_id=priced_offer.offer.offer_id,
            plan_kind=priced_offer.offer.emi_type,
            lender_label=priced_offer.offer.lender_label,
            tenure_in_months=priced_offer.offer.tenure_in_months,
            monthly_installment=priced_offer.quoted_monthly_installment,
            extra_in_total=priced_offer.schedule.extra_in_total,
            total_payable=priced_offer.schedule.total_payable,
        )

    def to_dictionary(self) -> ChosenPlanDictionary:
        """Encodes the plan as JSON-compatible text and integer paise for storage."""
        return {
            "offer_id": self.offer_id,
            "plan_kind": self.plan_kind.value,
            "lender_label": self.lender_label,
            "tenure_in_months": self.tenure_in_months,
            "monthly_installment_in_paise": self.monthly_installment.to_paise(),
            "extra_in_total_in_paise": self.extra_in_total.to_paise(),
            "total_payable_in_paise": self.total_payable.to_paise(),
        }

    @classmethod
    def from_dictionary(cls, stored_plan: Mapping[str, object]) -> "ChosenPlan":
        """Decodes a stored plan; any missing, extra or mistyped key raises, never guessed."""
        if set(stored_plan) != _ALL_KEYS:
            raise InvalidSaleDataError("A stored chosen plan must have exactly the known keys.")
        return cls(
            offer_id=_read_stored_value(stored_plan, "offer_id", str),
            plan_kind=_read_plan_kind(stored_plan),
            lender_label=_read_stored_value(stored_plan, "lender_label", str),
            tenure_in_months=_read_stored_value(stored_plan, "tenure_in_months", int),
            monthly_installment=_read_paise(stored_plan, "monthly_installment_in_paise"),
            extra_in_total=_read_paise(stored_plan, "extra_in_total_in_paise"),
            total_payable=_read_paise(stored_plan, "total_payable_in_paise"),
        )
