"""OfferDiscoveryService: the EMI offers for an item, each priced by our engine and checked."""

from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.core.clock import Clock
from emi_copilot.domain.events import OfferQuoteMismatch
from emi_copilot.domain.payments import OfferDiscoveryQuery, PricedEmiOffer, price_emi_offer
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory


class OfferDiscoveryService:
    """Asks the gateway for offers and pairs each quote with our exact schedule (ADR 0001).

    Every offer is returned in the gateway's order; ranking belongs to Layer 3. An offer whose
    quoted monthly figure is more than ₹1 from our schedule is audited as OFFER_QUOTE_MISMATCH
    and still returned, with the lender's figure shown (ADR 0011 decision 4).
    """

    def __init__(
        self,
        payment_gateway: PaymentGatewayPort,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        event_bus: DomainEventBus,
    ) -> None:
        """Keeps the gateway port, the unit-of-work factory for audits, the clock and the bus."""
        self._payment_gateway = payment_gateway
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._event_bus = event_bus

    def discover_offers(self, query: OfferDiscoveryQuery) -> tuple[PricedEmiOffer, ...]:
        """Gives every offer the gateway quotes for the item, priced; gateway errors propagate."""
        priced_offers = tuple(
            price_emi_offer(offer, query.price)
            for offer in self._payment_gateway.discover_offers(query)
        )
        mismatched_offers = [offer for offer in priced_offers if offer.has_quote_mismatch]
        if mismatched_offers:
            self._record_quote_mismatches(mismatched_offers)
        return priced_offers

    def _record_quote_mismatches(self, mismatched_offers: list[PricedEmiOffer]) -> None:
        """Publishes one OfferQuoteMismatch per offer, all in one unit of work."""
        occurred_at = self._clock.now()
        with self._unit_of_work_factory() as unit_of_work:
            for priced_offer in mismatched_offers:
                self._event_bus.publish(
                    OfferQuoteMismatch(
                        occurred_at=occurred_at,
                        offer_id=priced_offer.offer.offer_id,
                        tenure_in_months=priced_offer.offer.tenure_in_months,
                        price_in_paise=priced_offer.schedule.principal.to_paise(),
                        quoted_monthly_installment_in_paise=(
                            priced_offer.quoted_monthly_installment.to_paise()
                        ),
                        schedule_regular_installment_in_paise=(
                            priced_offer.schedule.regular_installment.to_paise()
                        ),
                        quoted_extra_in_total_in_paise=(
                            priced_offer.offer.quoted_extra_in_total.to_paise()
                        ),
                    ),
                    unit_of_work,
                )
