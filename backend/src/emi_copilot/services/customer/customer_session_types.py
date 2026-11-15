"""Inputs and results of the customer session services (C1 to C3), before they become wire DTOs."""

from dataclasses import dataclass, field
from datetime import datetime

from emi_copilot.domain.comfort import FinancialProfile
from emi_copilot.domain.customer_sessions import ComfortCheckStatus, CustomerLanguage
from emi_copilot.domain.money import Money


@dataclass(frozen=True, slots=True)
class CustomerSessionCredentials:
    """The session id from the path and the token from the X-Customer-Session-Token header.

    The token is kept out of repr, so a stray log line cannot leak it.
    """

    customer_session_id: str
    session_token: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class StartedCustomerSession:
    """What C1 shows after the QR is exchanged, with the token for every later call.

    The token is returned once and never stored; only its hash is.
    """

    customer_session_id: str
    session_token: str = field(repr=False)
    session_code: str
    shop_name: str
    product_name: str
    price: Money
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class CustomerSessionSummary:
    """The session as C1 shows it, plus the customer's own progress; never the token.

    language is None until the customer picks one on C1.
    """

    customer_session_id: str
    session_code: str
    shop_name: str
    product_name: str
    price: Money
    expires_at: datetime
    has_confirmed_budget: bool
    comfort_check_status: ComfortCheckStatus
    language: CustomerLanguage | None
    has_consented: bool


@dataclass(frozen=True, slots=True)
class ComfortCheckOutcome:
    """The C3 answer: COMPLETED with the profile read for the customer, or SKIPPED with none.

    is_synthetic_data says the profile comes from a labelled Mock, never real account data.
    """

    status: ComfortCheckStatus
    is_synthetic_data: bool
    financial_profile: FinancialProfile | None
