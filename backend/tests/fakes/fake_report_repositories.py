"""In-memory report queries and weekly message records that answer like the SQL ones."""

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime

from emi_copilot.domain.funnel import FunnelEvent, FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.reports.budget_buckets import build_budget_ranges
from emi_copilot.domain.reports.missed_sales import MissedSalesTally, is_missed_sale
from emi_copilot.domain.reports.weekly_message_record import WeeklyMessageSentRecord
from emi_copilot.domain.sales import Sale


class FakeReportQueryRepository:
    """Counts from the unit of work's copies of the sales and funnel events."""

    def __init__(self, sales_by_id: dict[str, Sale], funnel_events: list[FunnelEvent]) -> None:
        """Reads the unit of work's private copies; it never writes."""
        self._sales_by_id = sales_by_id
        self._funnel_events = funnel_events

    def _events_of_period(
        self, merchant_id: str, starts_at: datetime, ends_at: datetime
    ) -> list[tuple[Sale, FunnelEvent]]:
        """Pairs every funnel event of the merchant's sales started in the period with its sale."""
        return [
            (sale, event)
            for event in self._funnel_events
            for sale in (self._sales_by_id.get(event.sale_id),)
            if sale is not None
            and sale.merchant_id == merchant_id
            and starts_at <= sale.started_at < ends_at
        ]

    def count_sales_reaching_each_stage(
        self, merchant_id: str, starts_at: datetime, ends_at: datetime
    ) -> Mapping[FunnelStage, int]:
        """Counts the period's sales per stage reached."""
        return Counter(
            event.stage for _, event in self._events_of_period(merchant_id, starts_at, ends_at)
        )

    def count_budgets_per_range(
        self,
        merchant_id: str,
        starts_at: datetime,
        ends_at: datetime,
        range_boundaries: Sequence[Money],
    ) -> tuple[int, ...]:
        """Counts the period's told budgets per range, lower bound included."""
        budgets = [
            event.monthly_budget
            for _, event in self._events_of_period(merchant_id, starts_at, ends_at)
            if event.monthly_budget is not None
        ]
        return tuple(
            sum(1 for budget in budgets if budget_range.contains(budget))
            for budget_range in build_budget_ranges(range_boundaries)
        )

    def tally_missed_sales(
        self,
        merchant_id: str,
        starts_at: datetime,
        ends_at: datetime,
        budget_thresholds_by_product_id: Mapping[str, Money],
    ) -> Mapping[str, MissedSalesTally]:
        """Applies the domain rule is_missed_sale to each budget told in the period."""
        events = self._events_of_period(merchant_id, starts_at, ends_at)
        agreed_sale_ids = {sale.id for sale, event in events if event.stage is FunnelStage.AGREED}
        missed_budgets_by_product_id: dict[str, list[Money]] = {}
        for sale, event in events:
            if is_missed_sale(
                event.monthly_budget,
                sale.id in agreed_sale_ids,
                budget_thresholds_by_product_id.get(sale.product_id),
            ):
                missed_budgets_by_product_id.setdefault(sale.product_id, []).append(
                    event.monthly_budget  # type: ignore[arg-type]
                )
        return {
            product_id: MissedSalesTally(len(budgets), max(budgets))
            for product_id, budgets in missed_budgets_by_product_id.items()
        }


class FakeWeeklyMessageRepository:
    """Keeps sent moments per (merchant, week); the first record wins, as the unique key does."""

    def __init__(self, sent_at_by_week: dict[tuple[str, date], datetime]) -> None:
        """Works on the unit of work's private copy of the sent moments."""
        self._sent_at_by_week = sent_at_by_week

    def find_sent_at(self, merchant_id: str, period_start_date: date) -> datetime | None:
        """Gives the stored sent moment, or None."""
        return self._sent_at_by_week.get((merchant_id, period_start_date))

    def record_sent_once(
        self, weekly_message_id: str, merchant_id: str, period_start_date: date, sent_at: datetime
    ) -> WeeklyMessageSentRecord:
        """Stores the moment unless one is stored; the id is not kept by the fake."""
        del weekly_message_id
        stored_sent_at = self._sent_at_by_week.get((merchant_id, period_start_date))
        if stored_sent_at is not None:
            return WeeklyMessageSentRecord(stored_sent_at, was_sent_now=False)
        self._sent_at_by_week[(merchant_id, period_start_date)] = sent_at
        return WeeklyMessageSentRecord(sent_at, was_sent_now=True)
