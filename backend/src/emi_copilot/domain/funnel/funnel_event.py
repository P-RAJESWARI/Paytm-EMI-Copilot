"""FunnelEvent: the append-only fact that one sale reached one funnel stage."""

from dataclasses import dataclass
from datetime import datetime

from emi_copilot.domain.errors import InvalidSaleDataError
from emi_copilot.domain.funnel.funnel_stage import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_positive_whole_paise_money,
    require_timezone_aware_moment,
)


@dataclass(frozen=True, slots=True)
class FunnelEvent:
    """A sale reached a stage at a moment; each sale reaches each stage at most once.

    monthly_budget is the customer's confirmed monthly amount and exists exactly on the
    BUDGET_TOLD stage; the report uses it only inside aggregate budget buckets (step 2.4).
    """

    id: str
    sale_id: str
    merchant_id: str
    stage: FunnelStage
    occurred_at: datetime
    monthly_budget: Money | None = None

    def __post_init__(self) -> None:
        """Rejects blank ids, an unknown stage, a naive moment and a budget on the wrong stage."""
        for text, description in (
            (self.id, "funnel event id"),
            (self.sale_id, "sale id"),
            (self.merchant_id, "merchant id"),
        ):
            require_non_empty_text(text, description, InvalidSaleDataError)
        if not isinstance(self.stage, FunnelStage):
            raise InvalidSaleDataError("The funnel stage must be a FunnelStage.")
        require_timezone_aware_moment(self.occurred_at, "funnel moment", InvalidSaleDataError)
        is_budget_stage = self.stage is FunnelStage.BUDGET_TOLD
        if is_budget_stage != (self.monthly_budget is not None):
            raise InvalidSaleDataError("A monthly budget is recorded exactly on BUDGET_TOLD.")
        if self.monthly_budget is not None:
            require_positive_whole_paise_money(
                self.monthly_budget, "monthly budget", InvalidSaleDataError
            )
