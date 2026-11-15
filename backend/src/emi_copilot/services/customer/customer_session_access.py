"""CustomerSessionAccess: opens a customer's session from its token, and the sale behind it."""

from dataclasses import dataclass
from datetime import datetime

from emi_copilot.core.opaque_token import hash_opaque_token
from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.customer_sessions import CustomerSession
from emi_copilot.domain.errors import (
    BudgetNotConfirmedError,
    ConsentAlreadyGivenError,
    CustomerSessionNotFoundError,
    CustomerSessionTokenInvalidError,
    DomainError,
    InvalidSaleDataError,
    ProductNotFoundError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import OfferDiscoveryQuery
from emi_copilot.domain.sales import Sale, SaleStatus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.sale_expiry import SaleExpiryStep

INVALID_SESSION_LINK_DETAIL = "This session link is not valid; ask the shop for a new QR."
SALE_ENDED_DETAIL = "This sale has ended; ask the shop for a new QR."


@dataclass(frozen=True, slots=True)
class OpenedCustomerSale:
    """An active customer session and its sale, locked and expired first if overdue."""

    session: CustomerSession
    sale: Sale

    def find_choosing_refusal(self) -> DomainError | None:
        """Gives why a step before consent cannot run now, or None while the sale is CHOOSING.

        An expired sale ends the session (401, ask the shop for a new QR); a sale whose plan is
        already agreed refuses every step before consent (409 CONSENT_ALREADY_GIVEN).
        """
        if self.sale.status is SaleStatus.CHOOSING:
            return None
        if self.sale.status is SaleStatus.EXPIRED:
            return CustomerSessionTokenInvalidError(SALE_ENDED_DETAIL)
        return ConsentAlreadyGivenError("The plan for this sale was already agreed.")


def require_confirmed_budget(session: CustomerSession) -> Money:
    """Gives the session's confirmed monthly budget; raises BudgetNotConfirmedError without one."""
    if session.monthly_budget is None:
        raise BudgetNotConfirmedError("Confirm a monthly budget before this step.")
    return session.monthly_budget


def find_sale_product(unit_of_work: UnitOfWork, sale: Sale) -> CatalogueProduct:
    """Gives the sale's product from its shop's catalogue."""
    product = unit_of_work.products.find_by_id_for_merchant(sale.merchant_id, sale.product_id)
    if product is None:
        raise ProductNotFoundError("The product of a stored sale is not in the catalogue.")
    return product


def find_shop_name(unit_of_work: UnitOfWork, sale: Sale) -> str:
    """Gives the display name of the shop that started the sale."""
    merchant = unit_of_work.merchants.find_by_id(sale.merchant_id)
    if merchant is None:
        raise InvalidSaleDataError("The shop of a stored sale is not stored.")
    return merchant.display_name


def build_sale_offer_query(sale: Sale, product: CatalogueProduct) -> OfferDiscoveryQuery:
    """Gives the gateway query for the sale's product at the sale's price."""
    return OfferDiscoveryQuery(
        price=sale.price,
        product_id=product.gateway_product_id,
        brand_id=product.gateway_brand_id,
        category_id=product.gateway_category_id,
    )


class CustomerSessionAccess:
    """Checks a session token and opens the sale behind it inside the caller's unit of work.

    Probing gets one answer (ADR 0021 decision 4): a token that opens no active session is 401
    CUSTOMER_SESSION_TOKEN_INVALID, and a valid token used with any other session id is 404
    CUSTOMER_SESSION_NOT_FOUND, the same whether that id exists or not.
    """

    def __init__(self, sale_expiry: SaleExpiryStep) -> None:
        """Keeps the step that expires an overdue sale before a customer acts on it."""
        self._sale_expiry = sale_expiry

    def authenticate(
        self, unit_of_work: UnitOfWork, credentials: CustomerSessionCredentials, now: datetime
    ) -> CustomerSession:
        """Gives the active session the token opens; a revoked or expired one is refused."""
        session = unit_of_work.customer_sessions.find_by_token_hash(
            hash_opaque_token(credentials.session_token)
        )
        if session is None or not session.is_active(now):
            raise CustomerSessionTokenInvalidError(INVALID_SESSION_LINK_DETAIL)
        if session.id != credentials.customer_session_id:
            raise CustomerSessionNotFoundError("No customer session has this id.")
        return session

    def open_sale(
        self, unit_of_work: UnitOfWork, credentials: CustomerSessionCredentials, now: datetime
    ) -> OpenedCustomerSale:
        """Authenticates, then locks the session's sale and expires it if it is overdue.

        The caller raises any refusal only after the unit of work commits, so an expiry is kept.
        """
        return self.open_sale_of(
            unit_of_work, self.authenticate(unit_of_work, credentials, now), now
        )

    def open_sale_of(
        self, unit_of_work: UnitOfWork, session: CustomerSession, now: datetime
    ) -> OpenedCustomerSale:
        """Locks an authenticated session's sale and expires it if it is overdue."""
        sale = unit_of_work.sales.find_by_id_for_update(session.sale_id)
        if sale is None:
            raise CustomerSessionTokenInvalidError(INVALID_SESSION_LINK_DETAIL)
        return OpenedCustomerSale(
            session=session, sale=self._sale_expiry.expire_if_overdue(unit_of_work, sale, now)
        )
