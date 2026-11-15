"""CustomerSession: start, activity, budget, comfort check choice, language and revocation."""

from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from emi_copilot.domain.customer_sessions import (
    ComfortCheckStatus,
    CustomerLanguage,
    CustomerSession,
)
from emi_copilot.domain.errors import InvalidCustomerSessionDataError, InvalidMonthlyBudgetError
from emi_copilot.domain.money import Money
from tests.consent_builders import (
    CUSTOMER_SESSION_ID,
    SESSION_LIFETIME,
    SESSION_STARTED_AT,
    SYNTHETIC_SESSION_TOKEN_HASH,
    build_customer_session,
)
from tests.sale_builders import SALE_ID

LATER = SESSION_STARTED_AT + timedelta(minutes=5)


def test_start_gives_a_session_that_expires_after_its_lifetime_with_nothing_chosen() -> None:
    """A new session has no budget, no language, has not been asked about comfort, and is live."""
    customer_session = CustomerSession.start(
        customer_session_id=CUSTOMER_SESSION_ID,
        sale_id=SALE_ID,
        token_hash=SYNTHETIC_SESSION_TOKEN_HASH,
        started_at=SESSION_STARTED_AT,
        lifetime=SESSION_LIFETIME,
    )
    assert customer_session.expires_at == SESSION_STARTED_AT + timedelta(minutes=30)
    assert customer_session.monthly_budget is None
    assert customer_session.comfort_check_status is ComfortCheckStatus.NOT_ASKED
    assert customer_session.language is None
    assert customer_session.revoked_at is None


def test_is_active_is_true_until_the_expiry_moment_itself() -> None:
    """The expiry moment counts as expired, as for QR and device tokens."""
    customer_session = build_customer_session()
    assert customer_session.is_active(SESSION_STARTED_AT)
    assert customer_session.is_active(customer_session.expires_at - timedelta(microseconds=1))
    assert not customer_session.is_active(customer_session.expires_at)


def test_revoke_ends_the_session_and_keeps_the_first_revocation_moment() -> None:
    """A revoked session is no longer active; revoking again changes nothing."""
    revoked_session = build_customer_session().revoke(LATER)
    assert revoked_session.revoked_at == LATER
    assert not revoked_session.is_active(LATER)
    assert revoked_session.revoke(LATER + timedelta(minutes=1)) is revoked_session


def test_confirm_budget_records_the_monthly_amount_and_replaces_an_earlier_one() -> None:
    """The customer may correct the budget; the latest confirmed amount is kept."""
    first_budget = build_customer_session().confirm_budget(Money.from_rupees("30000"))
    corrected_budget = first_budget.confirm_budget(Money.from_rupees("3000"))
    assert corrected_budget.monthly_budget == Money.from_rupees("3000")


@pytest.mark.parametrize(
    "monthly_budget",
    [Money.from_paise(0), Money.from_rupees("3000.001")],
    ids=["zero", "sub-paise"],
)
def test_confirm_budget_refuses_zero_or_sub_paise_amounts(monthly_budget: Money) -> None:
    """A budget is whole-paise money above zero."""
    with pytest.raises(InvalidMonthlyBudgetError):
        build_customer_session().confirm_budget(monthly_budget)


@pytest.mark.parametrize(
    ("has_consented", "expected_status"),
    [(True, ComfortCheckStatus.COMPLETED), (False, ComfortCheckStatus.SKIPPED)],
)
def test_record_comfort_check_choice_records_completed_or_skipped(
    *, has_consented: bool, expected_status: ComfortCheckStatus
) -> None:
    """Allowing the check completes it; skipping is always allowed."""
    customer_session = build_customer_session().record_comfort_check_choice(
        has_consented=has_consented
    )
    assert customer_session.comfort_check_status is expected_status


def test_choose_language_records_the_language_for_every_later_screen() -> None:
    """The C1 choice carries into the receipt."""
    customer_session = build_customer_session().choose_language(CustomerLanguage.TAMIL)
    assert customer_session.language is CustomerLanguage.TAMIL
    assert CustomerLanguage.TAMIL.value == "ta"


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": " "},
        {"sale_id": ""},
        {"token_hash": "A" * 64},
        {"token_hash": "a" * 63},
        {"created_at": datetime(2026, 11, 26, 9, 30)},  # noqa: DTZ001 - a naive moment on purpose
        {"expires_at": datetime(2026, 11, 26, 10, 0)},  # noqa: DTZ001 - a naive moment on purpose
        {"expires_at": SESSION_STARTED_AT},
        {"revoked_at": datetime(2026, 11, 26, 9, 40)},  # noqa: DTZ001 - a naive moment on purpose
        {"revoked_at": SESSION_STARTED_AT - timedelta(seconds=1)},
        {"comfort_check_status": "COMPLETED"},
        {"language": "en"},
    ],
    ids=[
        "blank-id",
        "blank-sale",
        "uppercase-hash",
        "short-hash",
        "naive-start",
        "naive-expiry",
        "expiry-at-start",
        "naive-revocation",
        "revoked-before-start",
        "status-text",
        "language-text",
    ],
)
def test_customer_session_refuses_inconsistent_fields(overrides: dict[str, object]) -> None:
    """Invalid sessions cannot be built, so a repository can never load one."""
    with pytest.raises(InvalidCustomerSessionDataError):
        build_customer_session(**overrides)


def test_customer_session_refuses_a_stored_zero_budget() -> None:
    """A stored budget is checked like a confirmed one."""
    with pytest.raises(InvalidMonthlyBudgetError):
        replace(build_customer_session(), monthly_budget=Money.from_paise(0))
