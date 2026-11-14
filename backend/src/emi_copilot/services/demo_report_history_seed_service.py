"""DemoReportHistorySeedService: writes the demo shop's synthetic week so M5 shows the design.

Run by `make seed` after the shop and catalogue exist. Sales go through the Sale state machine
and the repositories (no raw SQL); funnel rows are appended like the live recorder appends them.
funnel_event is append-only, so history is never replaced: the step writes nothing when the
shop already has any sale. To reseed for the current week, reset the development database
(`make db-reset`) and seed again.
"""

import hashlib
import logging
import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.errors import InvalidMerchantDataError
from emi_copilot.domain.funnel import FunnelEvent, FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import PricedEmiOffer, price_emi_offer
from emi_copilot.domain.reports.funnel_report import FUNNEL_STAGE_ORDER
from emi_copilot.domain.reports.reporting_period import find_week_start_date
from emi_copilot.domain.sales import (
    ChosenPlan,
    CustomerQrTokenState,
    Sale,
    SalePaymentOutcome,
    SessionCode,
)
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork, UnitOfWorkFactory

seed_history_logger = logging.getLogger(__name__)

QR_TOKEN_LIFETIME = timedelta(minutes=15)
SHOP_OPENS_AT = time(10, 0)
MINUTES_BETWEEN_HISTORY_SALES = 7
MONDAY_HISTORY_MARGIN = timedelta(minutes=90)
STAGE_OFFSETS = {
    FunnelStage.STARTED: timedelta(0),
    FunnelStage.BUDGET_TOLD: timedelta(minutes=1),
    FunnelStage.PLANS_VIEWED: timedelta(minutes=2),
    FunnelStage.AGREED: timedelta(minutes=4),
    FunnelStage.PAID: timedelta(minutes=6),
}


class HistoryOutcome(StrEnum):
    """Where a seeded sale ends; only the merchant-visible statuses (plan Q2)."""

    CHOOSING = "CHOOSING"
    EXPIRED = "EXPIRED"
    READY_TO_PAY = "READY_TO_PAY"
    PAID = "PAID"
    PAYMENT_NOT_COMPLETED = "PAYMENT_NOT_COMPLETED"


@dataclass(frozen=True, slots=True)
class HistorySale:
    """One synthetic sale: product, last funnel stage, told budget and final status.

    A counter sale (today, on M2's list) names its session code and how long ago it started;
    every other sale is placed on earlier days of the week by the seed.
    """

    gateway_product_id: str
    last_stage: FunnelStage
    budget_in_rupees: str | None
    outcome: HistoryOutcome
    session_code: str | None = None
    minutes_before_now: int | None = None


@dataclass(frozen=True, slots=True)
class SeededSaleFacts:
    """Where and when one seeded sale happens: its product and quotes, code and moments."""

    product: CatalogueProduct
    priced_offers: tuple[PricedEmiOffer, ...]
    session_code: str
    started_at: datetime
    now: datetime


@dataclass(frozen=True, slots=True)
class DemoReportHistorySeedOutcome:
    """What one run did: how many sales it wrote (0 when the shop already had sales)."""

    added_sale_count: int


def schedule_history_moments(count: int, now: datetime, time_zone: ZoneInfo) -> list[datetime]:
    """Places sales on the week's earlier days from 10:00, round-robin, 7 minutes apart.

    On a Monday there is no earlier day, so they spread over the hours before now (minus a
    margin), and the counter list then also shows them: a known limit of a Monday demo.
    """
    local_now = now.astimezone(time_zone)
    week_start_date = find_week_start_date(local_now.date())
    day_count = (local_now.date() - week_start_date).days
    if day_count == 0:
        week_start = datetime.combine(week_start_date, time.min, tzinfo=time_zone)
        available = max(timedelta(0), local_now - MONDAY_HISTORY_MARGIN - week_start)
        return [week_start + available * index / max(count, 1) for index in range(count)]
    return [
        datetime.combine(week_start_date, SHOP_OPENS_AT, tzinfo=time_zone)
        + timedelta(
            days=index % day_count, minutes=MINUTES_BETWEEN_HISTORY_SALES * (index // day_count)
        )
        for index in range(count)
    ]


def choose_plan_within_budget(
    priced_offers: Sequence[PricedEmiOffer], budget: Money | None
) -> ChosenPlan:
    """Picks what a customer with this budget plausibly agreed to: the least extra that fits."""
    fitting = [
        offer
        for offer in priced_offers
        if budget is None or offer.quoted_monthly_installment <= budget
    ]
    candidates = fitting or list(priced_offers)
    chosen = min(
        candidates,
        key=lambda offer: (offer.schedule.extra_in_total, offer.quoted_monthly_installment),
    )
    return ChosenPlan.from_priced_offer(chosen)


class DemoReportHistorySeedService:
    """Writes one shop's synthetic week in one transaction, under the shop's row lock."""

    def __init__(  # noqa: PLR0913 - one parameter per collaborator
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        payment_gateway: PaymentGatewayPort,
        clock: Clock,
        id_generator: IdGenerator,
        time_zone: ZoneInfo,
        choosing_lifetime: timedelta,
    ) -> None:
        """Keeps the collaborators; the gateway quotes the plans the history agrees to."""
        self._unit_of_work_factory = unit_of_work_factory
        self._payment_gateway = payment_gateway
        self._clock = clock
        self._id_generator = id_generator
        self._time_zone = time_zone
        self._choosing_lifetime = choosing_lifetime

    def seed(self, shop_code: str, history: Sequence[HistorySale]) -> DemoReportHistorySeedOutcome:
        """Writes the history unless the shop has any sale already; the shop must exist."""
        now = self._clock.now()
        with self._unit_of_work_factory() as unit_of_work:
            merchant = unit_of_work.merchants.find_by_shop_code_for_update(shop_code)
            if merchant is None:
                raise InvalidMerchantDataError("Seed the demo shop before its report history.")
            if unit_of_work.sales.has_any_for_merchant(merchant.id):
                seed_history_logger.info(
                    "demo report history already present; run make db-reset to reseed",
                    extra={"merchant_id": merchant.id},
                )
                return DemoReportHistorySeedOutcome(added_sale_count=0)
            self._write_history(unit_of_work, merchant.id, history, now)
        return DemoReportHistorySeedOutcome(added_sale_count=len(history))

    def _write_history(
        self,
        unit_of_work: UnitOfWork,
        merchant_id: str,
        history: Sequence[HistorySale],
        now: datetime,
    ) -> None:
        """Quotes the shop's products, schedules the sales and writes each one."""
        products = {
            product.gateway_product_id: product
            for product in unit_of_work.products.list_for_merchant(merchant_id)
        }
        offers = {gateway_id: self._quote(product) for gateway_id, product in products.items()}
        history_moments = iter(
            schedule_history_moments(
                sum(1 for sale in history if sale.minutes_before_now is None), now, self._time_zone
            )
        )
        today_start = datetime.combine(
            now.astimezone(self._time_zone).date(), time.min, tzinfo=self._time_zone
        )
        for index, history_sale in enumerate(history):
            started_at = (
                next(history_moments)
                if history_sale.minutes_before_now is None
                else max(today_start, now - timedelta(minutes=history_sale.minutes_before_now))
            )
            self._write_sale(
                unit_of_work,
                history_sale,
                SeededSaleFacts(
                    product=products[history_sale.gateway_product_id],
                    priced_offers=offers[history_sale.gateway_product_id],
                    session_code=history_sale.session_code or f"{1000 + index:04d}",
                    started_at=started_at,
                    now=now,
                ),
            )

    def _quote(self, product: CatalogueProduct) -> tuple[PricedEmiOffer, ...]:
        """Asks the gateway for the product's plans and prices them with our engine."""
        return tuple(
            price_emi_offer(offer, product.list_price)
            for offer in self._payment_gateway.discover_offers(product.to_offer_discovery_query())
        )

    def _write_sale(
        self, unit_of_work: UnitOfWork, history_sale: HistorySale, facts: SeededSaleFacts
    ) -> None:
        """Moves one sale through the state machine and appends the stages it reached."""
        product, priced_offers, now = facts.product, facts.priced_offers, facts.now
        session_code, started_at = facts.session_code, facts.started_at
        budget = (
            None
            if history_sale.budget_in_rupees is None
            else Money.from_rupees(history_sale.budget_in_rupees)
        )
        sale = Sale.start(
            sale_id=self._id_generator.new_id(),
            merchant_id=product.merchant_id,
            product_id=product.id,
            price=product.list_price,
            session_code=SessionCode(session_code),
            qr_token=CustomerQrTokenState(
                nonce_hash=hashlib.sha256(secrets.token_bytes(32)).hexdigest(),
                expires_at=started_at + QR_TOKEN_LIFETIME,
            ),
            started_at=started_at,
            idempotency=None,
        )
        unit_of_work.sales.add(
            self._finish_sale(sale, history_sale.outcome, priced_offers, budget, now)
        )
        last_stage_index = FUNNEL_STAGE_ORDER.index(history_sale.last_stage)
        for stage in FUNNEL_STAGE_ORDER[: last_stage_index + 1]:
            unit_of_work.funnel_events.append(
                FunnelEvent(
                    id=self._id_generator.new_id(),
                    sale_id=sale.id,
                    merchant_id=sale.merchant_id,
                    stage=stage,
                    occurred_at=min(now, started_at + STAGE_OFFSETS[stage]),
                    monthly_budget=budget if stage is FunnelStage.BUDGET_TOLD else None,
                )
            )

    def _finish_sale(
        self,
        sale: Sale,
        outcome: HistoryOutcome,
        priced_offers: tuple[PricedEmiOffer, ...],
        budget: Money | None,
        now: datetime,
    ) -> Sale:
        """Applies the commands that lead a started sale to its seeded final status."""
        if outcome is HistoryOutcome.CHOOSING:
            return sale
        if outcome is HistoryOutcome.EXPIRED:
            return sale.expire(min(now, sale.started_at + self._choosing_lifetime))
        agreed_sale = sale.agree_to_plan(
            choose_plan_within_budget(priced_offers, budget),
            min(now, sale.started_at + STAGE_OFFSETS[FunnelStage.AGREED]),
        )
        if outcome is HistoryOutcome.READY_TO_PAY:
            return agreed_sale
        payment_outcome = (
            SalePaymentOutcome.PAID
            if outcome is HistoryOutcome.PAID
            else SalePaymentOutcome.NOT_COMPLETED
        )
        finished_sale, _ = agreed_sale.apply_payment_outcome(
            payment_outcome, min(now, sale.started_at + STAGE_OFFSETS[FunnelStage.PAID])
        )
        return finished_sale
