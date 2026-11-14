"""EmiOffer: one EMI plan exactly as the lender, through the gateway, quoted it."""

from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.emi_type import EmiType
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_positive_whole_paise_money,
    require_tenure_in_months,
    require_whole_paise_money,
)


# Pattern: Value Object. Keeps the lender's quote intact so our schedule can be checked against it.
@dataclass(frozen=True, slots=True)
class EmiOffer:
    """A quoted plan: the lender's monthly installment and extra cost, before any of our maths.

    It deliberately holds no schedule. Services build the schedule from the quoted extra with
    QuotedTotalStrategy and compare it with the quoted installment (ADR 0001). Invariants: amounts
    are whole paise, the installment is above zero, and a no-cost offer quotes no extra.
    """

    offer_id: str
    lender_label: str
    emi_type: EmiType
    tenure_in_months: int
    quoted_monthly_installment: Money
    quoted_extra_in_total: Money

    def __post_init__(self) -> None:
        """Rejects blank labels, a bad tenure, sub-paise amounts and a no-cost offer with extra."""
        require_non_empty_text(self.offer_id, "offer id", InvalidPaymentGatewayValueError)
        require_non_empty_text(self.lender_label, "lender label", InvalidPaymentGatewayValueError)
        if not isinstance(self.emi_type, EmiType):
            raise InvalidPaymentGatewayValueError("The EMI type must be an EmiType.")
        require_tenure_in_months(self.tenure_in_months, "tenure", InvalidPaymentGatewayValueError)
        require_positive_whole_paise_money(
            self.quoted_monthly_installment,
            "quoted monthly installment",
            InvalidPaymentGatewayValueError,
        )
        require_whole_paise_money(
            self.quoted_extra_in_total, "quoted extra in total", InvalidPaymentGatewayValueError
        )
        if self.emi_type is EmiType.NO_COST and not self.quoted_extra_in_total.is_zero:
            raise InvalidPaymentGatewayValueError("A no-cost offer quotes no extra in total.")
