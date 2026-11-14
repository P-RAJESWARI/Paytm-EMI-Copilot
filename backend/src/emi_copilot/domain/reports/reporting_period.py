"""ReportingPeriod: the shop-calendar span a report covers (today, this week or this month)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from emi_copilot.domain.errors import InvalidReportingPeriodError
from emi_copilot.domain.payments.field_validation import require_timezone_aware_moment

_DAYS_PER_WEEK = 7
_DECEMBER = 12


class ReportingRange(StrEnum):
    """Which span of the shop's calendar a report covers (M5's Today, This week, This month)."""

    TODAY = "TODAY"
    """The shop's current calendar day."""

    THIS_WEEK = "THIS_WEEK"
    """Monday 00:00 to Sunday 23:59:59.999999 in the shop's time zone (plan Q21)."""

    THIS_MONTH = "THIS_MONTH"
    """The first to the last day of the shop's current calendar month."""


def _local_midnight_in_utc(local_date: date, time_zone: ZoneInfo) -> datetime:
    """Gives the UTC moment of local midnight at the start of the date."""
    return datetime.combine(local_date, time.min, tzinfo=time_zone).astimezone(UTC)


def _first_day_of_next_month(local_date: date) -> date:
    """Gives the first day of the month after the date's month."""
    if local_date.month == _DECEMBER:
        return date(local_date.year + 1, 1, 1)
    return date(local_date.year, local_date.month + 1, 1)


# Pattern: Value Object. Time-zone maths for every report lives here once, not in queries.
@dataclass(frozen=True, slots=True)
class ReportingPeriod:
    """Whole local days as a half-open UTC range: starts_at <= moment < ends_at.

    period_start_date and period_end_date are the first and last local dates, both included, so
    "this week" ends on Sunday and its last moment is Sunday 23:59:59.999999 local time.
    """

    starts_at: datetime
    ends_at: datetime
    period_start_date: date
    period_end_date: date

    @classmethod
    def covering_local_dates(
        cls, first_date: date, last_date: date, time_zone: ZoneInfo
    ) -> "ReportingPeriod":
        """Gives the period from local midnight of first_date to local midnight after last_date."""
        if last_date < first_date:
            raise InvalidReportingPeriodError("A period cannot end before it starts.")
        return cls(
            starts_at=_local_midnight_in_utc(first_date, time_zone),
            ends_at=_local_midnight_in_utc(last_date + timedelta(days=1), time_zone),
            period_start_date=first_date,
            period_end_date=last_date,
        )

    @classmethod
    def containing(
        cls, reporting_range: ReportingRange, moment: datetime, time_zone: ZoneInfo
    ) -> "ReportingPeriod":
        """Gives today's, this week's or this month's period around the moment, in local time."""
        require_timezone_aware_moment(moment, "moment", InvalidReportingPeriodError)
        local_date = moment.astimezone(time_zone).date()
        if reporting_range is ReportingRange.TODAY:
            return cls.covering_local_dates(local_date, local_date, time_zone)
        if reporting_range is ReportingRange.THIS_WEEK:
            return cls.week_starting(find_week_start_date(local_date), time_zone)
        first_date = local_date.replace(day=1)
        last_date = _first_day_of_next_month(local_date) - timedelta(days=1)
        return cls.covering_local_dates(first_date, last_date, time_zone)

    @classmethod
    def week_starting(cls, monday: date, time_zone: ZoneInfo) -> "ReportingPeriod":
        """Gives the Monday-to-Sunday week that starts on the date; any other weekday is refused."""
        if monday.weekday() != 0:
            raise InvalidReportingPeriodError("A reporting week starts on a Monday.")
        return cls.covering_local_dates(
            monday, monday + timedelta(days=_DAYS_PER_WEEK - 1), time_zone
        )


def find_week_start_date(local_date: date) -> date:
    """Gives the Monday on or before the local date."""
    return local_date - timedelta(days=local_date.weekday())
