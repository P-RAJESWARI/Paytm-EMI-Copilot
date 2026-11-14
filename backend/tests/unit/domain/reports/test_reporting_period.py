"""ReportingPeriod: shop-calendar days, Monday-to-Sunday weeks and months, in IST from UTC."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from emi_copilot.domain.errors import InvalidReportingPeriodError
from emi_copilot.domain.reports.reporting_period import (
    ReportingPeriod,
    ReportingRange,
    find_week_start_date,
)

INDIA = ZoneInfo("Asia/Kolkata")
LAST_MOMENT_OF_SUNDAY_IST = datetime(2026, 11, 15, 18, 29, 59, 999999, tzinfo=UTC)
FIRST_MOMENT_OF_MONDAY_IST = datetime(2026, 11, 15, 18, 30, tzinfo=UTC)


def test_this_week_runs_monday_to_sunday_in_ist_as_utc_bounds() -> None:
    """Saturday 14 Nov 2026 lies in the week of Monday 9 to Sunday 15 November."""
    period = ReportingPeriod.containing(
        ReportingRange.THIS_WEEK, datetime(2026, 11, 14, 6, 0, tzinfo=UTC), INDIA
    )
    assert (period.period_start_date, period.period_end_date) == (
        date(2026, 11, 9),
        date(2026, 11, 15),
    )
    assert period.starts_at == datetime(2026, 11, 8, 18, 30, tzinfo=UTC)
    assert period.ends_at == FIRST_MOMENT_OF_MONDAY_IST


def test_sunday_23_59_59_999999_ist_is_still_this_week() -> None:
    """The last microsecond of Sunday in IST belongs to the week it ends."""
    period = ReportingPeriod.containing(ReportingRange.THIS_WEEK, LAST_MOMENT_OF_SUNDAY_IST, INDIA)
    assert period.period_start_date == date(2026, 11, 9)
    assert period.starts_at <= LAST_MOMENT_OF_SUNDAY_IST < period.ends_at


def test_monday_00_00_ist_starts_the_next_week_although_it_is_sunday_in_utc() -> None:
    """18:30 UTC on Sunday is already Monday in IST."""
    period = ReportingPeriod.containing(ReportingRange.THIS_WEEK, FIRST_MOMENT_OF_MONDAY_IST, INDIA)
    assert period.period_start_date == date(2026, 11, 16)
    assert period.starts_at == FIRST_MOMENT_OF_MONDAY_IST


def test_today_is_the_ist_calendar_day_even_when_utc_is_still_yesterday() -> None:
    """20:00 UTC on 14 November is 01:30 IST on 15 November."""
    period = ReportingPeriod.containing(
        ReportingRange.TODAY, datetime(2026, 11, 14, 20, 0, tzinfo=UTC), INDIA
    )
    assert (period.period_start_date, period.period_end_date) == (
        date(2026, 11, 15),
        date(2026, 11, 15),
    )
    assert period.ends_at - period.starts_at == timedelta(days=1)


@pytest.mark.parametrize(
    ("moment", "expected_first_date", "expected_last_date"),
    [
        (datetime(2026, 11, 14, 6, 0, tzinfo=UTC), date(2026, 11, 1), date(2026, 11, 30)),
        (datetime(2026, 12, 31, 18, 29, tzinfo=UTC), date(2026, 12, 1), date(2026, 12, 31)),
        (datetime(2026, 12, 31, 18, 30, tzinfo=UTC), date(2027, 1, 1), date(2027, 1, 31)),
        (datetime(2028, 2, 10, 6, 0, tzinfo=UTC), date(2028, 2, 1), date(2028, 2, 29)),
    ],
)
def test_this_month_covers_the_ist_calendar_month_including_year_ends_and_leap_days(
    moment: datetime, expected_first_date: date, expected_last_date: date
) -> None:
    """Month edges move with IST, so 18:30 UTC on 31 December is already January."""
    period = ReportingPeriod.containing(ReportingRange.THIS_MONTH, moment, INDIA)
    assert (period.period_start_date, period.period_end_date) == (
        expected_first_date,
        expected_last_date,
    )
    assert period.ends_at == datetime.combine(
        expected_last_date + timedelta(days=1), datetime.min.time(), tzinfo=INDIA
    ).astimezone(UTC)


def test_week_starting_refuses_a_date_that_is_not_a_monday() -> None:
    """Weeks always start on Monday (plan Q21)."""
    with pytest.raises(InvalidReportingPeriodError, match="Monday"):
        ReportingPeriod.week_starting(date(2026, 11, 10), INDIA)


def test_covering_local_dates_refuses_an_end_before_the_start() -> None:
    """A period is at least one day long."""
    with pytest.raises(InvalidReportingPeriodError, match="end before"):
        ReportingPeriod.covering_local_dates(date(2026, 11, 2), date(2026, 11, 1), INDIA)


def test_containing_refuses_a_moment_without_a_time_zone() -> None:
    """A naive moment would be read in an unknown zone."""
    with pytest.raises(InvalidReportingPeriodError, match="timezone-aware"):
        ReportingPeriod.containing(ReportingRange.TODAY, datetime(2026, 11, 14, 6, 0), INDIA)  # noqa: DTZ001


@pytest.mark.parametrize(
    ("local_date", "expected_monday"),
    [
        (date(2026, 11, 9), date(2026, 11, 9)),
        (date(2026, 11, 15), date(2026, 11, 9)),
        (date(2026, 11, 16), date(2026, 11, 16)),
    ],
)
def test_find_week_start_date_gives_the_monday_on_or_before(
    local_date: date, expected_monday: date
) -> None:
    """Monday is its own week start; Sunday belongs to the Monday before."""
    assert find_week_start_date(local_date) == expected_monday
