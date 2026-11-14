"""StartSaleService: starts a counter sale of one catalogue product and issues its first QR code."""

from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.core.session_code_generator import SessionCodeGenerator
from emi_copilot.domain.errors import (
    IdempotencyKeyReusedError,
    ProductNotFoundError,
    SessionCodesExhaustedError,
)
from emi_copilot.domain.events import SaleStarted
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.domain.sales import Sale, SaleIdempotency, SessionCode
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork, UnitOfWorkFactory
from emi_copilot.services.customer_qr_link_issuer import CustomerQrLinkIssuer
from emi_copilot.services.sale_expiry import SaleExpiryStep
from emi_copilot.services.sale_views import (
    CounterSale,
    StartedSale,
    StartSaleCommand,
    build_counter_sale,
)


class StartSaleService:
    """Starts a sale at the product's list price ("price at counter" is read-only, plan Q20).

    The shop's row is locked first, so two starts at once never take the same session code or
    both miss the same Idempotency-Key. The same key with the same body returns the stored sale
    (as it now stands, without a QR link, since raw tokens are never kept); with another body
    it raises IdempotencyKeyReusedError (api-conventions section 5).
    """

    def __init__(  # noqa: PLR0913 - a use case wired with its collaborators, by keyword
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        id_generator: IdGenerator,
        event_bus: DomainEventBus,
        session_code_generator: SessionCodeGenerator,
        qr_link_issuer: CustomerQrLinkIssuer,
        sale_expiry: SaleExpiryStep,
    ) -> None:
        """Keeps the collaborators every start needs."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._id_generator = id_generator
        self._event_bus = event_bus
        self._session_code_generator = session_code_generator
        self._qr_link_issuer = qr_link_issuer
        self._sale_expiry = sale_expiry

    def start_sale(self, principal: MerchantPrincipal, command: StartSaleCommand) -> StartedSale:
        """Starts the sale and its STARTED funnel row in one transaction, or replays the key."""
        idempotency = (
            None
            if command.idempotency_key is None
            else SaleIdempotency(command.idempotency_key, command.calculate_request_fingerprint())
        )
        with self._unit_of_work_factory() as unit_of_work:
            unit_of_work.merchants.lock_for_update(principal.merchant_id)
            if idempotency is not None:
                stored_sale = unit_of_work.sales.find_by_idempotency_key_for_merchant(
                    principal.merchant_id, idempotency.idempotency_key
                )
                if stored_sale is not None:
                    return self._replay(unit_of_work, stored_sale, idempotency)
            return self._start_new_sale(unit_of_work, principal, command.product_id, idempotency)

    def _replay(
        self, unit_of_work: UnitOfWork, stored_sale: Sale, idempotency: SaleIdempotency
    ) -> StartedSale:
        """Gives the sale an earlier request with this key started, or refuses a new body."""
        if stored_sale.idempotency != idempotency:
            raise IdempotencyKeyReusedError("The Idempotency-Key was used with a different body.")
        current_sale = self._sale_expiry.expire_if_overdue(
            unit_of_work, stored_sale, self._clock.now()
        )
        return StartedSale(
            counter_sale=build_counter_sale(unit_of_work, current_sale),
            qr_link=None,
            is_replay=True,
        )

    def _start_new_sale(
        self,
        unit_of_work: UnitOfWork,
        principal: MerchantPrincipal,
        product_id: str,
        idempotency: SaleIdempotency | None,
    ) -> StartedSale:
        """Adds a CHOOSING sale with a free code and a fresh QR token, and announces it."""
        product = unit_of_work.products.find_by_id_for_merchant(principal.merchant_id, product_id)
        if product is None:
            raise ProductNotFoundError("No product with this id is in the shop's catalogue.")
        sale_id = self._id_generator.new_id()
        issued_qr = self._qr_link_issuer.issue(sale_id)
        sale = Sale.start(
            sale_id=sale_id,
            merchant_id=principal.merchant_id,
            product_id=product.id,
            price=product.list_price,
            session_code=self._pick_free_session_code(unit_of_work, principal.merchant_id),
            qr_token=issued_qr.qr_token_state,
            started_at=self._clock.now(),
            idempotency=idempotency,
        )
        unit_of_work.sales.add(sale)
        self._announce_sale_started(unit_of_work, sale)
        return StartedSale(
            counter_sale=CounterSale(sale=sale, product_name=product.name),
            qr_link=issued_qr.link,
            is_replay=False,
        )

    def _announce_sale_started(self, unit_of_work: UnitOfWork, sale: Sale) -> None:
        """Publishes SaleStarted in the sale's transaction (audit row and STARTED funnel row)."""
        self._event_bus.publish(
            SaleStarted(
                occurred_at=sale.started_at,
                sale_id=sale.id,
                merchant_id=sale.merchant_id,
                product_id=sale.product_id,
                price_in_paise=sale.price.to_paise(),
            ),
            unit_of_work,
        )

    def _pick_free_session_code(self, unit_of_work: UnitOfWork, merchant_id: str) -> SessionCode:
        """Picks a code no open sale of the shop shows, or raises when all 10,000 are taken."""
        taken_codes = unit_of_work.sales.list_open_session_codes_for_merchant(merchant_id)
        free_code = self._session_code_generator.pick_free_code(taken_codes)
        if free_code is None:
            raise SessionCodesExhaustedError(
                "Every session code is on one of the shop's open sales."
            )
        return SessionCode(free_code)
