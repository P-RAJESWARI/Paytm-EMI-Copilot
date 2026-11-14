"""ReportPeriods: turns a report range or a week's Monday into a period on the shop's calendar."""

from datetime import date
from zoneinfo import ZoneInfo

from emi_copilot.core.clock import Clock
from emi_copilot.domain.errors import InvalidReportingPeriodError
from emi_copilot.domain.reports.reporting_period import (
    ReportingPeriod,
    ReportingRange,
    find_week_start_date,
)


class ReportPeriods:
    """Works out report periods from the injected clock in the reporting time zone (IST)."""

    def __init__(self, clock: Clock, time_zone: ZoneInfo) -> None:
        """Keeps the clock and the shop's time zone."""
        self._clock = clock
        self._time_zone = time_zone

    def containing_now(self, reporting_range: ReportingRange) -> ReportingPeriod:
        """Gives today's, this week's or this month's period."""
        return ReportingPeriod.containing(reporting_range, self._clock.now(), self._time_zone)

    def current_week_start_date(self) -> date:
        """Gives the Monday of the current week in the shop's time zone."""
        return find_week_start_date(self._clock.now().astimezone(self._time_zone).date())

    def week_starting(self, monday: date | None) -> ReportingPeriod:
        """Gives the week starting on the Monday (the current week when None).

        A date that is not a Monday, or a week after the current one, is refused.
        """
        current_monday = self.current_week_start_date()
        period = ReportingPeriod.week_starting(
            current_monday if monday is None else monday, self._time_zone
        )
        if period.period_start_date > current_monday:
            raise InvalidReportingPeriodError("A week that has not started has no report yet.")
        return period
