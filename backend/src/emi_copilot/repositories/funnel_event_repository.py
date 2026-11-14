"""Appends and reads funnel events; this repository deliberately has no update or delete method."""

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from emi_copilot.core.clock import Clock
from emi_copilot.domain.funnel import FunnelEvent, FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.models import FunnelEventModel


def _to_domain(funnel_event_model: FunnelEventModel) -> FunnelEvent:
    """Maps an ORM row back to a validated domain event; occurred_at is returned in UTC."""
    return FunnelEvent(
        id=funnel_event_model.id,
        sale_id=funnel_event_model.sale_id,
        merchant_id=funnel_event_model.merchant_id,
        stage=FunnelStage(funnel_event_model.stage),
        occurred_at=funnel_event_model.occurred_at.astimezone(UTC),
        monthly_budget=(
            None
            if funnel_event_model.monthly_budget_in_paise is None
            else Money.from_paise(funnel_event_model.monthly_budget_in_paise)
        ),
    )


# Pattern: Repository. The append-only funnel; the missing update/delete is the point.
class FunnelEventRepository:
    """Appends funnel events and reads one sale's back, inside the unit of work's session.

    A database trigger also rejects UPDATE, DELETE and TRUNCATE on funnel_event, and a unique
    constraint lets each sale reach each stage once.
    """

    def __init__(self, session: Session, clock: Clock) -> None:
        """Uses the unit of work's session and the injected clock for each row's created_at."""
        self._session = session
        self._clock = clock

    def append(self, funnel_event: FunnelEvent) -> None:
        """Inserts one funnel event, with any budget as integer paise, and flushes it now."""
        self._session.add(
            FunnelEventModel(
                id=funnel_event.id,
                sale_id=funnel_event.sale_id,
                merchant_id=funnel_event.merchant_id,
                stage=funnel_event.stage.value,
                occurred_at=funnel_event.occurred_at,
                monthly_budget_in_paise=(
                    None
                    if funnel_event.monthly_budget is None
                    else funnel_event.monthly_budget.to_paise()
                ),
                created_at=self._clock.now(),
            )
        )
        self._session.flush()

    def list_for_sale(self, sale_id: str) -> tuple[FunnelEvent, ...]:
        """Returns the stages one sale reached, oldest first."""
        funnel_event_models = self._session.scalars(
            select(FunnelEventModel)
            .where(FunnelEventModel.sale_id == sale_id)
            .order_by(FunnelEventModel.occurred_at, FunnelEventModel.id)
        ).all()
        return tuple(_to_domain(funnel_event_model) for funnel_event_model in funnel_event_models)
