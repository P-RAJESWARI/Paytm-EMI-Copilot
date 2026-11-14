"""OfferSnapshot value object: the exact EMI plan the customer was shown, frozen for evidence."""

from collections.abc import Mapping
from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidOfferSnapshotError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.emi_type import EmiType
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_whole_paise_money,
)

OfferSnapshotDictionary = dict[str, str | int]
"""The JSON-compatible form of a snapshot: text fields and integer paise, never floats."""

_TEXT_KEYS = ("offer_id", "lender_label", "emi_type")
_INTEGER_KEYS = (
    "tenure_in_months",
    "regular_installment_in_paise",
    "last_installment_in_paise",
    "total_payable_in_paise",
    "extra_in_total_in_paise",
)
_ALL_KEYS = frozenset(_TEXT_KEYS + _INTEGER_KEYS)


def _read_text(snapshot_dictionary: Mapping[str, object], key: str) -> str:
    """Reads one text field from a stored snapshot, rejecting any other type."""
    value = snapshot_dictionary[key]
    if not isinstance(value, str):
        raise InvalidOfferSnapshotError(f"The stored snapshot field {key!r} must be text.")
    return value


def _read_integer(snapshot_dictionary: Mapping[str, object], key: str) -> int:
    """Reads one integer field from a stored snapshot; bools and floats are rejected."""
    value = snapshot_dictionary[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidOfferSnapshotError(f"The stored snapshot field {key!r} must be an integer.")
    return value


def _read_emi_type(snapshot_dictionary: Mapping[str, object]) -> EmiType:
    """Reads the EMI type by its stored value, rejecting values this code does not know."""
    emi_type_value = _read_text(snapshot_dictionary, "emi_type")
    try:
        return EmiType(emi_type_value)
    except ValueError as unknown_value_error:
        raise InvalidOfferSnapshotError(
            f"The stored EMI type {emi_type_value!r} is not a known EmiType."
        ) from unknown_value_error


def _read_paise(snapshot_dictionary: Mapping[str, object], key: str) -> Money:
    """Reads one non-negative integer paise field as Money."""
    amount_in_paise = _read_integer(snapshot_dictionary, key)
    if amount_in_paise < 0:
        raise InvalidOfferSnapshotError(f"The stored snapshot field {key!r} cannot be negative.")
    return Money.from_paise(amount_in_paise)


# Pattern: Value Object. Immutable and self-consistent, so stored evidence matches what was shown.
@dataclass(frozen=True, slots=True)
class OfferSnapshot:
    """The plan shown to the customer: tenure - 1 regular installments, then one last installment.

    Invariants: every amount is whole-paise Money; the installments add up to the total payable
    exactly; the price (total payable minus extra in total) is above zero; a one-month plan has a
    single installment; a no-cost plan has no extra. It holds no card or personal data.
    """

    offer_id: str
    lender_label: str
    emi_type: EmiType
    tenure_in_months: int
    regular_installment: Money
    last_installment: Money
    total_payable: Money
    extra_in_total: Money

    def __post_init__(self) -> None:
        """Rejects missing labels, bad tenures, sub-paise amounts and inconsistent totals."""
        require_non_empty_text(self.offer_id, "offer id", InvalidOfferSnapshotError)
        require_non_empty_text(self.lender_label, "lender label", InvalidOfferSnapshotError)
        if not isinstance(self.emi_type, EmiType):
            raise InvalidOfferSnapshotError("The EMI type must be an EmiType.")
        self._require_valid_tenure()
        for amount, description in (
            (self.regular_installment, "regular installment"),
            (self.last_installment, "last installment"),
            (self.total_payable, "total payable"),
            (self.extra_in_total, "extra in total"),
        ):
            require_whole_paise_money(amount, description, InvalidOfferSnapshotError)
        self._require_consistent_amounts()

    def _require_valid_tenure(self) -> None:
        """Raises unless the tenure is a whole number of months, at least one."""
        if isinstance(self.tenure_in_months, bool) or not isinstance(self.tenure_in_months, int):
            raise InvalidOfferSnapshotError("The tenure must be a whole number of months.")
        if self.tenure_in_months < 1:
            raise InvalidOfferSnapshotError("The tenure must be at least 1 month.")

    def _require_consistent_amounts(self) -> None:
        """Raises unless the installments, total and extra agree with each other exactly."""
        installments_sum = (
            self.regular_installment * (self.tenure_in_months - 1) + self.last_installment
        )
        if installments_sum != self.total_payable:
            raise InvalidOfferSnapshotError("The installments must add up to the total payable.")
        if self.tenure_in_months == 1 and self.regular_installment != self.last_installment:
            raise InvalidOfferSnapshotError("A one-month plan has a single installment.")
        if self.extra_in_total >= self.total_payable:
            raise InvalidOfferSnapshotError("The extra in total must be below the total payable.")
        if self.emi_type is EmiType.NO_COST and not self.extra_in_total.is_zero:
            raise InvalidOfferSnapshotError("A no-cost plan has no extra in total.")

    def to_dictionary(self) -> OfferSnapshotDictionary:
        """Encodes the snapshot as JSON-compatible text and integer paise for storage."""
        return {
            "offer_id": self.offer_id,
            "lender_label": self.lender_label,
            "emi_type": self.emi_type.value,
            "tenure_in_months": self.tenure_in_months,
            "regular_installment_in_paise": self.regular_installment.to_paise(),
            "last_installment_in_paise": self.last_installment.to_paise(),
            "total_payable_in_paise": self.total_payable.to_paise(),
            "extra_in_total_in_paise": self.extra_in_total.to_paise(),
        }

    @classmethod
    def from_dictionary(cls, snapshot_dictionary: Mapping[str, object]) -> "OfferSnapshot":
        """Decodes a stored snapshot; any missing, extra or mistyped key raises, never guessed."""
        if set(snapshot_dictionary) != _ALL_KEYS:
            raise InvalidOfferSnapshotError("A stored snapshot must have exactly the known keys.")
        return cls(
            offer_id=_read_text(snapshot_dictionary, "offer_id"),
            lender_label=_read_text(snapshot_dictionary, "lender_label"),
            emi_type=_read_emi_type(snapshot_dictionary),
            tenure_in_months=_read_integer(snapshot_dictionary, "tenure_in_months"),
            regular_installment=_read_paise(snapshot_dictionary, "regular_installment_in_paise"),
            last_installment=_read_paise(snapshot_dictionary, "last_installment_in_paise"),
            total_payable=_read_paise(snapshot_dictionary, "total_payable_in_paise"),
            extra_in_total=_read_paise(snapshot_dictionary, "extra_in_total_in_paise"),
        )
