"""IssueQrTokenService: a fresh customer QR code for a sale that is still CHOOSING."""

from emi_copilot.core.clock import Clock
from emi_copilot.domain.errors import IllegalSaleTransitionError
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.customer_qr_link_issuer import CustomerQrLinkIssuer
from emi_copilot.services.sale_expiry import SaleExpiryStep
from emi_copilot.services.sale_views import CustomerQrLink


class IssueQrTokenService:
    """Replaces a CHOOSING sale's QR token, which voids the previous one (its hash is replaced).

    Any other status raises IllegalSaleTransitionError (409). The refusal is raised after the
    transaction commits, so an expiry found on the way is kept.
    """

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        qr_link_issuer: CustomerQrLinkIssuer,
        sale_expiry: SaleExpiryStep,
    ) -> None:
        """Keeps the unit-of-work factory, the clock, the QR issuer and the expiry step."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._qr_link_issuer = qr_link_issuer
        self._sale_expiry = sale_expiry

    def issue_qr_token(self, principal: MerchantPrincipal, sale_id: str) -> CustomerQrLink:
        """Gives the new QR link, or raises SaleNotFoundError or IllegalSaleTransitionError."""
        refusal: IllegalSaleTransitionError | None = None
        with self._unit_of_work_factory() as unit_of_work:
            sale = self._sale_expiry.load_current_sale_for_update(
                unit_of_work, principal.merchant_id, sale_id, self._clock.now()
            )
            issued_qr = self._qr_link_issuer.issue(sale.id)
            try:
                reissued_sale = sale.issue_qr_token(issued_qr.qr_token_state)
            except IllegalSaleTransitionError as transition_refusal:
                refusal = transition_refusal
            else:
                unit_of_work.sales.update(reissued_sale)
        if refusal is not None:
            raise refusal
        return issued_qr.link
