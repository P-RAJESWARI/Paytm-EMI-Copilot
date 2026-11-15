"""CustomerSession entity: one phone's access to one sale, from the QR exchange to its expiry."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Self

from emi_copilot.domain.customer_sessions.comfort_check_status import ComfortCheckStatus
from emi_copilot.domain.customer_sessions.customer_language import CustomerLanguage
from emi_copilot.domain.errors import InvalidCustomerSessionDataError, InvalidMonthlyBudgetError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_positive_whole_paise_money,
    require_sha256_hex,
    require_timezone_aware_moment,
)


def _require_moment(value: object, description: str) -> None:
    """Raises unless the value is a timezone-aware datetime."""
    require_timezone_aware_moment(value, description, InvalidCustomerSessionDataError)


@dataclass(frozen=True, slots=True)
class CustomerSession:
    """A customer's session on one sale, known by the hash of its random token (ADR 0022).

    It is immutable: each step returns a new session that the repository saves. The token itself
    is never stored. It holds the confirmed monthly budget and the comfort check choice, never
    income or existing EMIs, and it is never shown to the merchant (CLAUDE.md rule 6).
    """

    id: str
    sale_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    monthly_budget: Money | None = None
    comfort_check_status: ComfortCheckStatus = ComfortCheckStatus.NOT_ASKED
    language: CustomerLanguage | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        """Rejects blank ids, a malformed token hash, bad moments, budget, status or language."""
        require_non_empty_text(self.id, "customer session id", InvalidCustomerSessionDataError)
        require_non_empty_text(self.sale_id, "sale id", InvalidCustomerSessionDataError)
        require_sha256_hex(self.token_hash, "session token hash", InvalidCustomerSessionDataError)
        self._require_consistent_moments()
        if self.monthly_budget is not None:
            require_positive_whole_paise_money(
                self.monthly_budget, "monthly budget", InvalidMonthlyBudgetError
            )
        if not isinstance(self.comfort_check_status, ComfortCheckStatus):
            raise InvalidCustomerSessionDataError("The comfort check status is not known.")
        if self.language is not None and not isinstance(self.language, CustomerLanguage):
            raise InvalidCustomerSessionDataError("The language must be a CustomerLanguage.")

    def _require_consistent_moments(self) -> None:
        """Raises unless every moment has a time zone and expiry and revocation follow the start."""
        _require_moment(self.created_at, "session start")
        _require_moment(self.expires_at, "session expiry")
        if self.expires_at <= self.created_at:
            raise InvalidCustomerSessionDataError("A session must expire after it starts.")
        if self.revoked_at is not None:
            _require_moment(self.revoked_at, "session revocation")
            if self.revoked_at < self.created_at:
                raise InvalidCustomerSessionDataError("A session cannot end before it starts.")

    @classmethod
    def start(
        cls,
        *,
        customer_session_id: str,
        sale_id: str,
        token_hash: str,
        started_at: datetime,
        lifetime: timedelta,
    ) -> Self:
        """Starts a session that lasts the given lifetime, with no budget and nothing chosen."""
        return cls(
            id=customer_session_id,
            sale_id=sale_id,
            token_hash=token_hash,
            created_at=started_at,
            expires_at=started_at + lifetime,
        )

    def is_active(self, now: datetime) -> bool:
        """Tells whether the token still opens the session: not revoked and before its expiry.

        The expiry moment itself counts as expired, as for QR tokens and device tokens.
        """
        return self.revoked_at is None and now < self.expires_at

    def confirm_budget(self, monthly_budget: Money) -> Self:
        """Records the monthly amount the customer confirmed on C2, replacing any earlier one."""
        return replace(self, monthly_budget=monthly_budget)

    def record_comfort_check_choice(self, *, has_consented: bool) -> Self:
        """Records that the customer allowed the comfort check (COMPLETED) or skipped it (C3)."""
        chosen_status = (
            ComfortCheckStatus.COMPLETED if has_consented else ComfortCheckStatus.SKIPPED
        )
        return replace(self, comfort_check_status=chosen_status)

    def choose_language(self, language: CustomerLanguage) -> Self:
        """Records the language chosen on C1, which every later screen and the receipt use."""
        return replace(self, language=language)

    def revoke(self, now: datetime) -> Self:
        """Ends the session now, as when a new QR is exchanged; an earlier revocation is kept."""
        if self.revoked_at is not None:
            return self
        return replace(self, revoked_at=now)
