"""Shared field checks for payment value objects and entities; each raises the caller's error."""

from datetime import datetime

from emi_copilot.domain.errors import DomainError
from emi_copilot.domain.money import Money


def require_non_empty_text(value: object, description: str, error_type: type[DomainError]) -> None:
    """Raises error_type unless the value is a string with at least one non-blank character."""
    if not isinstance(value, str) or not value.strip():
        raise error_type(f"The {description} must be non-empty text.")


def require_optional_non_empty_text(
    value: object, description: str, error_type: type[DomainError]
) -> None:
    """Raises error_type unless the value is None or non-empty text; blank means absent, so None."""
    if value is not None:
        require_non_empty_text(value, description, error_type)


def require_whole_paise_money(
    value: object, description: str, error_type: type[DomainError]
) -> None:
    """Raises error_type unless the value is Money with no precision below one paisa."""
    if not isinstance(value, Money) or not value.is_whole_paise:
        raise error_type(f"The {description} must be Money in whole paise.")


def require_timezone_aware_moment(
    value: object, description: str, error_type: type[DomainError]
) -> None:
    """Raises error_type unless the value is a timezone-aware datetime, so no moment is unclear."""
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise error_type(f"The {description} must be a timezone-aware datetime.")
