"""SessionCode is four digits; CounterDay is the local IST day as a half-open UTC range."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from emi_copilot.domain.errors import InvalidSaleDataError
from emi_copilot.domain.sales import SESSION_CODE_DIGIT_COUNT, CounterDay, SessionCode

INDIA_TIME_ZONE = ZoneInfo("Asia/Kolkata")


@pytest.mark.parametrize("code", ["0000", "4821", "9999"])
def test_session_code_accepts_exactly_four_digits_with_leading_zeros(code: str) -> None:
    """A code such as 0042 keeps its leading zeros: it is a label, not a number."""
    assert SessionCode(code).value == code
    assert len(code) == SESSION_CODE_DIGIT_COUNT


@pytest.mark.parametrize("code", ["482", "48210", "48a1", "٤٨٢١", " 4821", 4821])
def test_session_code_refuses_anything_else(code: object) -> None:
    """Short, long, lettered, non-ASCII digits, padded and integer values are refused."""
    with pytest.raises(InvalidSaleDataError):
        SessionCode(code)  # type: ignore[arg-type]


def test_counter_day_gives_ist_midnight_to_midnight_in_utc() -> None:
    """15 Nov 2026 IST runs from 14 Nov 18:30 UTC to 15 Nov 18:30 UTC."""
    counter_day = CounterDay.containing(datetime(2026, 11, 15, 9, 0, tzinfo=UTC), INDIA_TIME_ZONE)
    assert counter_day == CounterDay(
        starts_at=datetime(2026, 11, 14, 18, 30, tzinfo=UTC),
        ends_at=datetime(2026, 11, 15, 18, 30, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    ("moment", "expected_start"),
    [
        (
            datetime(2026, 11, 14, 18, 29, 59, tzinfo=UTC),
            datetime(2026, 11, 13, 18, 30, tzinfo=UTC),
        ),
        (datetime(2026, 11, 14, 18, 30, tzinfo=UTC), datetime(2026, 11, 14, 18, 30, tzinfo=UTC)),
    ],
)
def test_counter_day_boundary_is_local_midnight(moment: datetime, expected_start: datetime) -> None:
    """23:59:59 IST belongs to that day; 00:00 IST already belongs to the next."""
    counter_day = CounterDay.containing(moment, INDIA_TIME_ZONE)
    assert counter_day.starts_at == expected_start
    assert counter_day.ends_at - counter_day.starts_at == timedelta(days=1)


def test_counter_day_of_a_naive_moment_raises() -> None:
    """A moment without a time zone has no local day."""
    with pytest.raises(InvalidSaleDataError):
        CounterDay.containing(datetime(2026, 11, 15, 9, 0), INDIA_TIME_ZONE)  # noqa: DTZ001
