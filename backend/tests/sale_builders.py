"""Builders of valid sales, chosen plans and funnel events with synthetic values only."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from emi_copilot.domain.funnel import FunnelEvent, FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import EmiType
from emi_copilot.domain.sales import (
    STATUSES_WITH_CHOSEN_PLAN,
    ChosenPlan,
    CustomerQrTokenState,
    Sale,
    SaleStatus,
    SessionCode,
)
from tests.merchant_builders import MERCHANT_ID

SALE_STARTED_AT = datetime(2026, 11, 14, 10, 30, tzinfo=UTC)
SALE_ID = "01JCSALE000000000000000001"
PRODUCT_ID = "01JCPRODUCT000000000000001"
SYNTHETIC_NONCE_HASH = "e" * 64
QR_TOKEN_LIFETIME = timedelta(minutes=15)
CHOOSING_LIFETIME = timedelta(hours=1)


def build_no_cost_chosen_plan(**overrides: object) -> ChosenPlan:
    """Design plan A on ₹22,000 as shown: ₹3,666.67 a month for 6 months, nothing extra."""
    chosen_plan = ChosenPlan(
        offer_id="offer-plan-a",
        plan_kind=EmiType.NO_COST,
        lender_label="Brand",
        tenure_in_months=6,
        monthly_installment=Money.from_rupees("3666.67"),
        extra_in_total=Money.from_paise(0),
        total_payable=Money.from_rupees("22000"),
    )
    return replace(chosen_plan, **overrides)  # type: ignore[arg-type]


def build_standard_chosen_plan() -> ChosenPlan:
    """Design plan B on ₹22,000 as shown: ₹3,850 a month for 6 months, ₹1,100 extra."""
    return ChosenPlan(
        offer_id="offer-plan-b",
        plan_kind=EmiType.STANDARD,
        lender_label="Your card's bank",
        tenure_in_months=6,
        monthly_installment=Money.from_rupees("3850"),
        extra_in_total=Money.from_rupees("1100"),
        total_payable=Money.from_rupees("23100"),
    )


def build_qr_token_state(**overrides: object) -> CustomerQrTokenState:
    """A QR token issued at SALE_STARTED_AT that lasts 15 minutes and is not exchanged."""
    qr_token_state = CustomerQrTokenState(
        nonce_hash=SYNTHETIC_NONCE_HASH, expires_at=SALE_STARTED_AT + QR_TOKEN_LIFETIME
    )
    return replace(qr_token_state, **overrides)  # type: ignore[arg-type]


def build_sale(**overrides: object) -> Sale:
    """A ₹22,000 CHOOSING sale of MERCHANT_ID started at SALE_STARTED_AT.

    A status that needs a chosen plan gets design plan A unless a chosen plan is given.
    """
    fields: dict[str, object] = {
        "id": SALE_ID,
        "merchant_id": MERCHANT_ID,
        "product_id": PRODUCT_ID,
        "price": Money.from_rupees("22000"),
        "session_code": SessionCode("4821"),
        "status": SaleStatus.CHOOSING,
        "chosen_plan": None,
        "qr_token": build_qr_token_state(),
        "started_at": SALE_STARTED_AT,
        "status_changed_at": SALE_STARTED_AT,
    }
    fields.update(overrides)
    if "chosen_plan" not in overrides and fields["status"] in STATUSES_WITH_CHOSEN_PLAN:
        fields["chosen_plan"] = build_no_cost_chosen_plan()
    return Sale(**fields)  # type: ignore[arg-type]


def build_funnel_event(**overrides: object) -> FunnelEvent:
    """The STARTED funnel event of the sample sale."""
    funnel_event = FunnelEvent(
        id="01JCFUNNELEVENT00000000001",
        sale_id=SALE_ID,
        merchant_id=MERCHANT_ID,
        stage=FunnelStage.STARTED,
        occurred_at=SALE_STARTED_AT,
    )
    return replace(funnel_event, **overrides)  # type: ignore[arg-type]
