"""ConsentPlanSnapshot value object: the exact plan and product the customer agreed to."""

from collections.abc import Mapping
from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidConsentDataError, InvalidSaleDataError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import require_non_empty_text
from emi_copilot.domain.sales.chosen_plan import ChosenPlan

ConsentPlanSnapshotDictionary = dict[str, str | int | dict[str, str | int]]
"""The JSON-compatible stored form: text, integer paise and the chosen plan's own dictionary."""

_ALL_KEYS = frozenset({"product_id", "product_name", "price_in_paise", "chosen_plan"})


def _read_text(stored_snapshot: Mapping[str, object], key: str) -> str:
    """Reads one stored text field; anything else raises."""
    value = stored_snapshot[key]
    if not isinstance(value, str):
        raise InvalidConsentDataError(f"The stored plan snapshot field {key!r} must be text.")
    return value


def _read_chosen_plan(stored_snapshot: Mapping[str, object]) -> ChosenPlan:
    """Decodes the nested chosen plan, reporting its problems as consent data problems."""
    stored_plan = stored_snapshot["chosen_plan"]
    if not isinstance(stored_plan, Mapping):
        raise InvalidConsentDataError("The stored plan snapshot needs a chosen plan mapping.")
    try:
        return ChosenPlan.from_dictionary(stored_plan)
    except InvalidSaleDataError as invalid_plan_error:
        raise InvalidConsentDataError(invalid_plan_error.detail) from invalid_plan_error


def _read_price(stored_snapshot: Mapping[str, object]) -> Money:
    """Reads the stored price in integer paise; bools and other types raise."""
    price_in_paise = stored_snapshot["price_in_paise"]
    if isinstance(price_in_paise, bool) or not isinstance(price_in_paise, int):
        raise InvalidConsentDataError("The stored plan snapshot price must be integer paise.")
    return Money.from_paise(price_in_paise)


# Pattern: Value Object. Frozen consent evidence: the figures shown on C9 for this product, so
# the record proves exactly what was agreed (CLAUDE.md section 2, rule 8).
@dataclass(frozen=True, slots=True)
class ConsentPlanSnapshot:
    """The product and its price, plus the agreed plan exactly as shown (Layer 2's ChosenPlan).

    The price is stored explicitly as evidence and must equal the plan's total minus its extra.
    """

    product_id: str
    product_name: str
    price: Money
    chosen_plan: ChosenPlan

    def __post_init__(self) -> None:
        """Rejects blank product fields, a missing plan and a price the plan was not quoted on."""
        require_non_empty_text(self.product_id, "product id", InvalidConsentDataError)
        require_non_empty_text(self.product_name, "product name", InvalidConsentDataError)
        if not isinstance(self.chosen_plan, ChosenPlan):
            raise InvalidConsentDataError("A plan snapshot needs the ChosenPlan shown.")
        if self.price != self.chosen_plan.price:
            raise InvalidConsentDataError("The plan must be quoted on the product's price.")

    def to_dictionary(self) -> ConsentPlanSnapshotDictionary:
        """Encodes the snapshot as JSON text and integer paise, for storage and hashing."""
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "price_in_paise": self.price.to_paise(),
            "chosen_plan": self.chosen_plan.to_dictionary(),
        }

    @classmethod
    def from_dictionary(cls, stored_snapshot: Mapping[str, object]) -> "ConsentPlanSnapshot":
        """Decodes a stored snapshot; any missing, extra or mistyped key raises, never guessed."""
        if set(stored_snapshot) != _ALL_KEYS:
            raise InvalidConsentDataError(
                "A stored plan snapshot must have exactly the known keys."
            )
        return cls(
            product_id=_read_text(stored_snapshot, "product_id"),
            product_name=_read_text(stored_snapshot, "product_name"),
            price=_read_price(stored_snapshot),
            chosen_plan=_read_chosen_plan(stored_snapshot),
        )
