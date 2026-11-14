"""The shop's calendar day around a moment, for the counter list of today's sales."""

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from emi_copilot.domain.errors import InvalidSaleDataError
from emi_copilot.domain.payments.field_validation import require_timezone_aware_moment


# Pattern: Value Object. Local-midnight maths lives here once, not in queries or services.
@dataclass(frozen=True, slots=True)
class CounterDay:
    """One local calendar day as a half-open UTC range: starts_at <= moment < ends_at."""

    starts_at: datetime
    ends_at: datetime

    @classmethod
    def containing(cls, moment: datetime, time_zone: ZoneInfo) -> "CounterDay":
        """Gives the local day (in the shop's time zone, IST for the demo) that holds the moment.

        Both ends are local midnights converted to UTC, so a sale started at 23:59 IST belongs
        to that day and one at 00:00 IST to the next.
        """
        require_timezone_aware_moment(moment, "moment", InvalidSaleDataError)
        local_date = moment.astimezone(time_zone).date()
        local_start = datetime.combine(local_date, time.min, tzinfo=time_zone)
        local_end = datetime.combine(local_date + timedelta(days=1), time.min, tzinfo=time_zone)
        return cls(starts_at=local_start.astimezone(UTC), ends_at=local_end.astimezone(UTC))
