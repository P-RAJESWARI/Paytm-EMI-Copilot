"""STUB until Phase 3C: gateway quotes priced by the EMI engine, without the mismatch audit."""

from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.domain.payments import OfferDiscoveryQuery, PricedEmiOffer, price_emi_offer


# Pattern: Adapter (stub). Presents PaymentGatewayPort as a PricedOfferSource with no database;
# Phase 3C wires OfferDiscoveryService instead, which also audits quote mismatches.
class StubGatewayPricedOfferSource:
    """STUB until Phase 3C: asks the gateway for offers and prices each on the item's price."""

    def __init__(self, payment_gateway: PaymentGatewayPort) -> None:
        """Keeps the gateway port (the Mock in the Phase 3A contract application)."""
        self._payment_gateway = payment_gateway

    def discover_offers(self, query: OfferDiscoveryQuery) -> tuple[PricedEmiOffer, ...]:
        """Gives every offer quoted for the item, priced by the engine, in the gateway's order."""
        return tuple(
            price_emi_offer(offer, query.price)
            for offer in self._payment_gateway.discover_offers(query)
        )
