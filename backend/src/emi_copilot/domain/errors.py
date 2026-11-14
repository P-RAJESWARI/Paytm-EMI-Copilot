"""Typed domain errors; each carries a stable machine-readable code for problem+json responses."""

from typing import ClassVar


class DomainError(Exception):
    """Base class for every business-rule violation raised by domain code."""

    code: ClassVar[str] = "DOMAIN_ERROR"

    def __init__(self, detail: str) -> None:
        """Stores an English, developer-facing explanation that never contains personal data."""
        super().__init__(detail)
        self.detail = detail


class InvalidMoneyAmountError(DomainError):
    """Raised when a value cannot be, or cannot become, a valid Money amount."""

    code: ClassVar[str] = "INVALID_MONEY_AMOUNT"


class InvalidEmiTermsError(DomainError):
    """Raised when EMI inputs are unusable, so no schedule can even be attempted.

    Examples: a principal that is zero, not Money or not whole paise; a tenure below one month; a
    negative, non-finite or non-Decimal rate; a quoted extra that is not whole-paise Money.
    """

    code: ClassVar[str] = "INVALID_EMI_TERMS"


class EmiScheduleNotRepresentableError(DomainError):
    """Raised when valid terms cannot give non-negative whole-paise installments.

    This happens only for tiny amounts over long tenures, where the n - 1 rounded regular
    installments already exceed the total, so the last installment would have to be negative.
    """

    code: ClassVar[str] = "EMI_SCHEDULE_NOT_REPRESENTABLE"
