"""Aggregate report queries over one shop's sales and funnel; no customer row ever leaves here.

Every method takes the merchant id and a half-open period [starts_at, ends_at) on the sale's
start (a cohort: sales started in the period, counted by the stages they reached). Each returns
counts, or a count and the highest budget per product; never a sale, an id or one budget per row.

A sale still CHOOSING is in no cohort (CLAUDE.md rule 6, ADR 0018): counting it would let the
merchant watch one live customer tell a budget and view the plans. A sale enters the reports
once it is READY_TO_PAY, PAID, PAYMENT_NOT_COMPLETED or EXPIRED, states the counter list already
shows. An overdue CHOOSING sale enters once its expiry is recorded (SaleExpiryStep runs on every
counter read and sale command).
"""

from collections.abc import Mapping, Sequence
from datetime import datetime

from sqlalchemy import BigInteger, ColumnElement, case, cast, exists, func, select
from sqlalchemy.dialects.postgresql import ARRAY, array
from sqlalchemy.orm import Session, aliased

from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.reports.missed_sales import MissedSalesTally
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.models import FunnelEventModel, SaleModel

_BudgetEvent = aliased(FunnelEventModel, name="budget_event")
_AgreedEvent = aliased(FunnelEventModel, name="agreed_event")


def _sale_in_period(
    merchant_id: str, starts_at: datetime, ends_at: datetime
) -> ColumnElement[bool]:
    """Selects the merchant's sales started in [starts_at, ends_at) that are no longer CHOOSING."""
    return (
        (SaleModel.merchant_id == merchant_id)
        & (SaleModel.started_at >= starts_at)
        & (SaleModel.started_at < ends_at)
        & (SaleModel.status != SaleStatus.CHOOSING.value)
    )


def _budget_event_of_sale(merchant_id: str) -> ColumnElement[bool]:
    """Joins a sale to its BUDGET_TOLD event in the same shop."""
    return (
        (_BudgetEvent.sale_id == SaleModel.id)
        & (_BudgetEvent.merchant_id == merchant_id)
        & (_BudgetEvent.stage == FunnelStage.BUDGET_TOLD.value)
    )


def _is_missed_sale(budget_thresholds_by_product_id: Mapping[str, Money]) -> ColumnElement[bool]:
    """Selects missed sales: a budget told below the product's threshold, and never AGREED.

    The threshold is the product's cheapest no-extra-cost monthly amount.
    """
    product_threshold_in_paise = case(
        {
            product_id: threshold.to_paise()
            for product_id, threshold in budget_thresholds_by_product_id.items()
        },
        value=SaleModel.product_id,
    )
    has_agreed = exists().where(
        (_AgreedEvent.sale_id == SaleModel.id) & (_AgreedEvent.stage == FunnelStage.AGREED.value)
    )
    return (
        SaleModel.product_id.in_(list(budget_thresholds_by_product_id))
        & (_BudgetEvent.monthly_budget_in_paise < product_threshold_in_paise)
        & ~has_agreed
    )


def _to_missed_sales_tally(
    missed_count: int, highest_budget_in_paise: int | None
) -> MissedSalesTally:
    """Turns one product's aggregate row into its tally, the highest budget as Money."""
    return MissedSalesTally(
        missed_count,
        None if highest_budget_in_paise is None else Money.from_paise(highest_budget_in_paise),
    )


# Pattern: Repository. Report SQL lives here, so services and the domain never build queries.
class ReportQueryRepository:
    """Counts one shop's funnel stages, budget ranges and missed sales in the unit of work."""

    def __init__(self, session: Session) -> None:
        """Uses the unit of work's session; it only reads."""
        self._session = session

    def count_sales_reaching_each_stage(
        self, merchant_id: str, starts_at: datetime, ends_at: datetime
    ) -> Mapping[FunnelStage, int]:
        """Counts the period's sales per stage reached; a stage nobody reached is absent."""
        statement = (
            select(FunnelEventModel.stage, func.count())
            .join(SaleModel, SaleModel.id == FunnelEventModel.sale_id)
            .where(
                _sale_in_period(merchant_id, starts_at, ends_at)
                & (FunnelEventModel.merchant_id == merchant_id)
            )
            .group_by(FunnelEventModel.stage)
        )
        return {
            FunnelStage(stage): customer_count
            for stage, customer_count in self._session.execute(statement).all()
        }

    def count_budgets_per_range(
        self,
        merchant_id: str,
        starts_at: datetime,
        ends_at: datetime,
        range_boundaries: Sequence[Money],
    ) -> tuple[int, ...]:
        """Counts the period's told budgets per range, one more count than boundaries.

        The ranges are below the first boundary, between each pair, and from the last one up;
        each includes its lower boundary (PostgreSQL width_bucket).
        """
        boundaries_in_paise = [boundary.to_paise() for boundary in range_boundaries]
        range_index = func.width_bucket(
            _BudgetEvent.monthly_budget_in_paise,
            cast(array(boundaries_in_paise), ARRAY(BigInteger)),
        )
        statement = (
            select(range_index, func.count())
            .select_from(SaleModel)
            .join(_BudgetEvent, _budget_event_of_sale(merchant_id))
            .where(_sale_in_period(merchant_id, starts_at, ends_at))
            .group_by(range_index)
        )
        counts_by_index: dict[int, int] = dict(self._session.execute(statement).all())
        return tuple(counts_by_index.get(index, 0) for index in range(len(boundaries_in_paise) + 1))

    def tally_missed_sales(
        self,
        merchant_id: str,
        starts_at: datetime,
        ends_at: datetime,
        budget_thresholds_by_product_id: Mapping[str, Money],
    ) -> Mapping[str, MissedSalesTally]:
        """Tallies the period's missed sales per product (domain rule is_missed_sale, in SQL).

        Products without a threshold, and products with no missed sale, are absent.
        """
        if not budget_thresholds_by_product_id:
            return {}
        statement = (
            select(
                SaleModel.product_id,
                func.count(),
                func.max(_BudgetEvent.monthly_budget_in_paise),
            )
            .join(_BudgetEvent, _budget_event_of_sale(merchant_id))
            .where(_sale_in_period(merchant_id, starts_at, ends_at))
            .where(_is_missed_sale(budget_thresholds_by_product_id))
            .group_by(SaleModel.product_id)
        )
        return {
            product_id: _to_missed_sales_tally(missed_count, highest_budget_in_paise)
            for product_id, missed_count, highest_budget_in_paise in self._session.execute(
                statement
            ).all()
        }
