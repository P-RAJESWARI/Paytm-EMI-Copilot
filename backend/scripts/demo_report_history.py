"""The demo shop's synthetic week: exactly the DESIGN_SPEC section 4 report for THIS_WEEK.

120 started, 96 told a budget, 88 saw the plans, 51 agreed, 44 paid (biggest drop: 37 after
seeing the plans). Budgets per range 5, 7, 14, 21, 49 (96). The 12 budgets under ₹3,000 are the
12 missed sales, all on the 128 GB phone (cheapest no-cost plan ₹3,666.67). Every other budget
below its product's cheapest no-cost monthly belongs to a sale that agreed, and the 8 who left
before the plans told budgets at or above it. Today's three M2 counter sales are 4812 PAID
(earbuds), 4817 READY_TO_PAY (64 GB phone, no-cost plan) and 4821 CHOOSING (128 GB). A sale
still CHOOSING is in no report (CLAUDE.md rule 6), so 4821 is not one of the 120: 121 sales are
seeded, and one more 128 GB customer who left before telling a budget (EXPIRED earlier this
week) takes the place 4821 used to fill. Once 4821 itself expires (an hour after the seed, on
the next counter read) it joins the week and STARTED reads 121; reseed for the exact design.
Synthetic data, never labelled on screen (DESIGN_SPEC section 1).
"""

from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_EARBUDS_PRODUCT_ID,
    MOCK_PHONE_64_GB_PRODUCT_ID,
    MOCK_PHONE_128_GB_PRODUCT_ID,
)
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.services.demo_report_history_seed_service import HistoryOutcome, HistorySale

PHONE_128 = MOCK_PHONE_128_GB_PRODUCT_ID
PHONE_64 = MOCK_PHONE_64_GB_PRODUCT_ID
EARBUDS = MOCK_EARBUDS_PRODUCT_ID


def _sales(
    gateway_product_id: str,
    last_stage: FunnelStage,
    outcome: HistoryOutcome,
    budgets_in_rupees: tuple[str | None, ...],
) -> tuple[HistorySale, ...]:
    """Gives one history sale per budget (None for a sale that never told one)."""
    return tuple(
        HistorySale(gateway_product_id, last_stage, budget_in_rupees, outcome)
        for budget_in_rupees in budgets_in_rupees
    )


def _amounts(*amounts_in_rupees: int) -> tuple[str, ...]:
    """Writes whole-rupee budgets as the decimal strings Money is built from."""
    return tuple(str(amount) for amount in amounts_in_rupees)


EXPIRED = HistoryOutcome.EXPIRED
PAID = HistoryOutcome.PAID
NOT_COMPLETED = HistoryOutcome.PAYMENT_NOT_COMPLETED

LEFT_BEFORE_TELLING_A_BUDGET = (
    _sales(PHONE_128, FunnelStage.STARTED, EXPIRED, (None,) * 13)
    + _sales(PHONE_64, FunnelStage.STARTED, EXPIRED, (None,) * 7)
    + _sales(EARBUDS, FunnelStage.STARTED, EXPIRED, (None,) * 4)
)
"""24 history sales: the drop of 24 after STARTED (today's 4821, still choosing, is not counted)."""

LEFT_BEFORE_SEEING_THE_PLANS = _sales(
    PHONE_128, FunnelStage.BUDGET_TOLD, EXPIRED, _amounts(3700, 3800, 3900, 4000, 4200, 4500)
) + _sales(PHONE_64, FunnelStage.BUDGET_TOLD, EXPIRED, _amounts(5000, 6000))
"""8 budgets, each at or above its product's cheapest no-cost monthly."""

MISSED_SALES = _sales(
    PHONE_128,
    FunnelStage.PLANS_VIEWED,
    EXPIRED,
    _amounts(2000, 2100, 2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900, 2950, 2990),
)
"""The 12 missed sales: 5 under ₹2,500 and 7 from ₹2,500 to ₹3,000, all on the 128 GB phone."""

LEFT_AFTER_SEEING_THE_PLANS = (
    _sales(PHONE_128, FunnelStage.PLANS_VIEWED, EXPIRED, _amounts(3700, 3750, 3800, 3850, 3900))
    + _sales(PHONE_128, FunnelStage.PLANS_VIEWED, EXPIRED, _amounts(3950))
    + _sales(PHONE_64, FunnelStage.PLANS_VIEWED, EXPIRED, _amounts(3500, 3600))
    + _sales(
        PHONE_128,
        FunnelStage.PLANS_VIEWED,
        EXPIRED,
        _amounts(4000, 4100, 4200, 4300, 4400, 4500, 4800, 5000, 5500, 6000, 7000),
    )
    + _sales(PHONE_64, FunnelStage.PLANS_VIEWED, EXPIRED, _amounts(4000, 4500, 5000))
    + _sales(EARBUDS, FunnelStage.PLANS_VIEWED, EXPIRED, _amounts(4000, 4500, 5000))
)
"""25 more who saw the plans and left, none under their product's cheapest no-cost monthly."""

AGREED_NOT_PAID = _sales(
    PHONE_128, FunnelStage.AGREED, NOT_COMPLETED, _amounts(3100, 3300, 3400, 4000, 4500, 5000)
)
"""6 payments not completed; with today's 4817 that is the drop of 7 after AGREED."""

PAID_SALES = (
    _sales(PHONE_128, FunnelStage.PAID, PAID, _amounts(3000, 3050, 3100, 3150, 3200, 3250))
    + _sales(PHONE_64, FunnelStage.PAID, PAID, _amounts(3000, 3100, 3300, 3450))
    + _sales(PHONE_128, FunnelStage.PAID, PAID, _amounts(3700, 3750, 3800, 3850, 3900, 3990))
    + _sales(PHONE_64, FunnelStage.PAID, PAID, _amounts(3500, 3600, 3700, 3800))
    + _sales(
        PHONE_128,
        FunnelStage.PAID,
        PAID,
        _amounts(4000, 4100, 4200, 4300, 4500, 4600, 4800, 5000),
    )
    + _sales(
        PHONE_128,
        FunnelStage.PAID,
        PAID,
        _amounts(5200, 5500, 6000, 6500, 7000, 8000, 9000, 10000),
    )
    + _sales(PHONE_64, FunnelStage.PAID, PAID, _amounts(4000, 4500, 5000))
    + _sales(EARBUDS, FunnelStage.PAID, PAID, _amounts(4000, 4200, 4800, 5000))
)
"""43 paid history sales; with today's 4812 that is 44."""

TODAYS_COUNTER_SALES = (
    HistorySale(EARBUDS, FunnelStage.PAID, "4500", PAID, "4812", minutes_before_now=30),
    HistorySale(PHONE_64, FunnelStage.AGREED, "3200", HistoryOutcome.READY_TO_PAY, "4817", 12),
    HistorySale(PHONE_128, FunnelStage.STARTED, None, HistoryOutcome.CHOOSING, "4821", 3),
)
"""M2's "At the counter now": started today, so the counter list shows exactly these three.

4812 and 4817 are in the reports; 4821 is CHOOSING, so no report counts it while it is.
"""

DEMO_REPORT_HISTORY = (
    LEFT_BEFORE_TELLING_A_BUDGET
    + LEFT_BEFORE_SEEING_THE_PLANS
    + MISSED_SALES
    + LEFT_AFTER_SEEING_THE_PLANS
    + AGREED_NOT_PAID
    + PAID_SALES
    + TODAYS_COUNTER_SALES
)
"""All 121 seeded sales: the 120 of the design week's reports, and 4821 still choosing."""
