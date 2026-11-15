"""Customer requests carry their session credentials and the customer's language."""

import pytest

from emi_copilot.api.customer_request_context import (
    choose_customer_language,
    provide_customer_language,
    provide_customer_session_credentials,
    read_language_quality,
)
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.errors import CustomerSessionTokenInvalidError


@pytest.mark.parametrize(
    ("accept_language", "expected_language"),
    [
        (None, CustomerLanguage.ENGLISH),
        ("", CustomerLanguage.ENGLISH),
        ("ta", CustomerLanguage.TAMIL),
        ("en", CustomerLanguage.ENGLISH),
        ("TA-in", CustomerLanguage.TAMIL),
        ("ta-IN,ta;q=0.9,en;q=0.8", CustomerLanguage.TAMIL),
        ("en-US,en;q=0.9,ta;q=0.8", CustomerLanguage.ENGLISH),
        ("en;q=0.5, ta;q=0.7", CustomerLanguage.TAMIL),
        ("hi-IN,hi;q=0.9", CustomerLanguage.ENGLISH),
        ("hi,ta;q=0.4", CustomerLanguage.TAMIL),
        ("ta;q=0,en;q=0.1", CustomerLanguage.ENGLISH),
        ("ta;q=abc", CustomerLanguage.ENGLISH),
        ("*", CustomerLanguage.ENGLISH),
    ],
)
def test_choose_customer_language_reads_browser_lists_and_defaults_to_english(
    accept_language: str | None, expected_language: CustomerLanguage
) -> None:
    """The preferred of en and ta wins by q-value, then order; anything else means English."""
    assert choose_customer_language(accept_language) is expected_language


@pytest.mark.parametrize(
    ("parameters", "expected_quality"),
    [
        ("", "1"),
        (" q=0.5", "0.5"),
        ("level=1; Q=0.25", "0.25"),
        ("q=", "0"),
        ("q=NaN", "0"),
        ("q=Infinity", "0"),
    ],
)
def test_read_language_quality_gives_one_when_absent_and_zero_when_unreadable(
    parameters: str, expected_quality: str
) -> None:
    """A missing q-value means full preference; an unreadable one means none."""
    assert str(read_language_quality(parameters)) == expected_quality


def test_provide_customer_language_defaults_to_english_without_the_header() -> None:
    """No Accept-Language header means English."""
    assert provide_customer_language() is CustomerLanguage.ENGLISH


def test_provide_customer_session_credentials_pairs_the_path_id_and_the_token() -> None:
    """The token stays out of repr, so a stray log line cannot leak it."""
    credentials = provide_customer_session_credentials("01JCSESSION", "synthetic-token")
    assert credentials.customer_session_id == "01JCSESSION"
    assert credentials.session_token == "synthetic-token"  # noqa: S105 - synthetic test value
    assert "synthetic-token" not in repr(credentials)


@pytest.mark.parametrize("missing_token", [None, ""])
def test_provide_customer_session_credentials_without_a_token_is_401(
    missing_token: str | None,
) -> None:
    """A missing X-Customer-Session-Token is our calm 401, never a framework 403."""
    with pytest.raises(CustomerSessionTokenInvalidError, match="ask the shop for a new QR"):
        provide_customer_session_credentials("01JCSESSION", missing_token)
