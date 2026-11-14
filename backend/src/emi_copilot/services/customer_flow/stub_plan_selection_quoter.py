"""STUB until Phase 3C: re-quotes the exact plan selection a consent names (ADR 0021)."""

from emi_copilot.domain.alternatives import DownPaymentRule
from emi_copilot.domain.errors import (
    InvalidPlanSelectionError,
    OfferNotFoundError,
    ShownPlanChangedError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import OfferDiscoveryQuery, PricedEmiOffer
from emi_copilot.services.customer_flow.customer_flow_types import (
    ConsentedPlan,
    GiveConsentCommand,
)
from emi_copilot.services.customer_flow.stub_design_sample import (
    STUB_CHEAPER_MODEL,
    STUB_ITEM,
    STUB_ITEM_PRODUCT_NAME,
)
from emi_copilot.services.plan_advice_types import PricedOfferSource


class StubPlanSelectionQuoter:
    """STUB until Phase 3C: quotes the session's item or the 64 GB model, less any down payment.

    The down payment must be zero or exactly the DownPaymentRule suggestion for the chosen plan.
    The fresh quote must match the figures the customer was shown, or nothing is recorded.
    """

    def __init__(
        self, offer_source: PricedOfferSource, down_payment_rule: DownPaymentRule | None = None
    ) -> None:
        """Keeps the offer source and the down-payment rule (ADR 0020 by default)."""
        self._offer_source = offer_source
        self._down_payment_rule = down_payment_rule or DownPaymentRule()

    def quote_selection(self, command: GiveConsentCommand, monthly_budget: Money) -> ConsentedPlan:
        """Re-quotes the selection and checks it against what was shown; raises on any change."""
        product_id, product_name, item = _resolve_product(command.product_id)
        full_price_plan = _find_quoted_plan(
            self._offer_source.discover_offers(item), command.offer_id
        )
        selected_plan = full_price_plan
        if not command.down_payment.is_zero:
            suggested_down_payment = self._down_payment_rule.suggest_down_payment(
                full_price_plan, monthly_budget
            )
            if command.down_payment != suggested_down_payment:
                raise InvalidPlanSelectionError("This down payment is not offered for this plan.")
            reduced_item = OfferDiscoveryQuery(
                price=item.price - command.down_payment,
                product_id=item.product_id,
                brand_id=item.brand_id,
                category_id=item.category_id,
            )
            selected_plan = _find_quoted_plan(
                self._offer_source.discover_offers(reduced_item), command.offer_id
            )
        _require_shown_figures(selected_plan, command)
        return ConsentedPlan(
            offer_snapshot=selected_plan.to_offer_snapshot(),
            product_id=product_id,
            product_name=product_name,
            price=item.price,
            down_payment=command.down_payment,
            financed_amount=selected_plan.schedule.principal,
        )


def _resolve_product(product_id: str | None) -> tuple[str, str, OfferDiscoveryQuery]:
    """Gives the id, name and query of the session's item or the 64 GB model; else raises."""
    if product_id is None or product_id == STUB_ITEM.product_id:
        return STUB_ITEM.product_id, STUB_ITEM_PRODUCT_NAME, STUB_ITEM
    if product_id == STUB_CHEAPER_MODEL.product_id:
        return (
            STUB_CHEAPER_MODEL.product_id,
            STUB_CHEAPER_MODEL.product_name,
            STUB_CHEAPER_MODEL.to_offer_discovery_query(),
        )
    raise InvalidPlanSelectionError("This product is not offered in this session.")


def _find_quoted_plan(priced_offers: tuple[PricedEmiOffer, ...], offer_id: str) -> PricedEmiOffer:
    """Gives the quoted plan with the offer id; raises OfferNotFoundError when it is absent."""
    for priced_offer in priced_offers:
        if priced_offer.offer.offer_id == offer_id:
            return priced_offer
    raise OfferNotFoundError("The chosen offer is not quoted for this item and price.")


def _require_shown_figures(selected_plan: PricedEmiOffer, command: GiveConsentCommand) -> None:
    """Raises ShownPlanChangedError when the monthly or total shown differs from the quote."""
    if (
        selected_plan.quoted_monthly_installment != command.shown_monthly_installment
        or selected_plan.schedule.total_payable != command.shown_total_payable
    ):
        raise ShownPlanChangedError("The plan figures changed; show the plans again.")
