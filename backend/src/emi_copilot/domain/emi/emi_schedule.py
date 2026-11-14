"""EmiSchedule value object and the one shared rule for splitting a total into installments."""

from dataclasses import dataclass

from emi_copilot.domain.errors import EmiScheduleNotRepresentableError, InvalidEmiTermsError
from emi_copilot.domain.money import Money


def _require_whole_paise_money(value: object, description: str) -> None:
    """Raises unless the value is Money with no precision below one paisa."""
    if not isinstance(value, Money) or not value.is_whole_paise:
        raise InvalidEmiTermsError(f"The {description} must be Money in whole paise.")


def require_valid_emi_terms(principal: Money, tenure_in_months: int) -> None:
    """Raises unless the principal is positive whole-paise Money and the tenure is at least a month.

    A zero principal is rejected: there is nothing to pay in installments, so a zero-rupee plan
    would only be a bug upstream.
    """
    _require_whole_paise_money(principal, "principal")
    if principal.is_zero:
        raise InvalidEmiTermsError("The principal must be above zero rupees.")
    if isinstance(tenure_in_months, bool) or not isinstance(tenure_in_months, int):
        raise InvalidEmiTermsError("The tenure must be a whole number of months.")
    if tenure_in_months < 1:
        raise InvalidEmiTermsError(f"The tenure must be at least 1 month, got {tenure_in_months}.")


# Pattern: Value Object. A schedule that is valid on creation and sums to its total by design.
@dataclass(frozen=True, slots=True)
class EmiSchedule:
    """An EMI schedule: tenure - 1 equal regular installments, then one last installment.

    Only the two installment amounts are stored, so the total payable is always exactly their
    sum. The last installment absorbs the rounding remainder. For a one-month plan the single
    installment is both the regular and the last one, so the two must be equal.
    """

    principal: Money
    tenure_in_months: int
    regular_installment: Money
    last_installment: Money

    def __post_init__(self) -> None:
        """Rejects invalid terms, sub-paise installments and totals below the principal."""
        require_valid_emi_terms(self.principal, self.tenure_in_months)
        _require_whole_paise_money(self.regular_installment, "regular installment")
        _require_whole_paise_money(self.last_installment, "last installment")
        if self.tenure_in_months == 1 and self.regular_installment != self.last_installment:
            raise InvalidEmiTermsError("A one-month schedule has a single installment.")
        if self.total_payable < self.principal:
            raise InvalidEmiTermsError("A schedule never collects less than its principal.")

    @property
    def installments(self) -> tuple[Money, ...]:
        """Lists every installment in payment order; the count always equals the tenure."""
        return (self.regular_installment,) * (self.tenure_in_months - 1) + (self.last_installment,)

    @property
    def total_payable(self) -> Money:
        """Gives the exact sum of all installments."""
        return self.regular_installment * (self.tenure_in_months - 1) + self.last_installment

    @property
    def extra_in_total(self) -> Money:
        """Gives what the customer pays on top of the principal over the whole plan."""
        return self.total_payable - self.principal


def split_total_payable_evenly(
    principal: Money, tenure_in_months: int, total_payable: Money
) -> EmiSchedule:
    """Splits a known total into equal half-up rounded installments; the last takes the remainder.

    Raises EmiScheduleNotRepresentableError when tenure - 1 rounded installments already exceed
    the total (only tiny totals over long tenures), since the last installment would be negative.
    """
    require_valid_emi_terms(principal, tenure_in_months)
    _require_whole_paise_money(total_payable, "total payable")
    regular_installment = (total_payable / tenure_in_months).rounded_to_paise()
    regular_installments_sum = regular_installment * (tenure_in_months - 1)
    if regular_installments_sum > total_payable:
        raise EmiScheduleNotRepresentableError(
            f"{total_payable} rupees cannot be split into {tenure_in_months} non-negative "
            "whole-paise installments with the remainder on the last one."
        )
    return EmiSchedule(
        principal=principal,
        tenure_in_months=tenure_in_months,
        regular_installment=regular_installment,
        last_installment=total_payable - regular_installments_sum,
    )
