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
