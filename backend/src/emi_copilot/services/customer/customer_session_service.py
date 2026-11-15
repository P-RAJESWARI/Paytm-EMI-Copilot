"""CustomerSessionService: trades a single-use QR token for a customer session (C1)."""

import hmac
from collections.abc import Callable
from datetime import datetime, timedelta

from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.core.opaque_token import IssuedOpaqueToken, issue_opaque_token
from emi_copilot.core.qr_token_signer import (
    QrTokenClaims,
    QrTokenRejectedError,
    QrTokenSigner,
    hash_qr_token_nonce,
)
from emi_copilot.domain.customer_sessions import CustomerSession
from emi_copilot.domain.errors import CustomerQrTokenInvalidError
from emi_copilot.domain.events import CustomerSessionStarted
from emi_copilot.domain.sales import Sale, SaleStatus
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork, UnitOfWorkFactory
from emi_copilot.services.customer.customer_session_access import (
    CustomerSessionAccess,
    find_sale_product,
    find_shop_name,
)
from emi_copilot.services.customer.customer_session_types import (
    CustomerSessionCredentials,
    CustomerSessionSummary,
    StartedCustomerSession,
)
from emi_copilot.services.sale_expiry import SaleExpiryStep

INVALID_QR_CODE_DETAIL = "This QR code is not valid; ask the shop for a new QR."

SessionTokenIssuer = Callable[[], IssuedOpaqueToken]
"""Draws a new random session token and its hash; tests inject a predictable one."""


def _is_exchangeable(sale: Sale, claims: QrTokenClaims) -> bool:
    """Tells whether the claims name the sale's current, unexchanged token while CHOOSING."""
    return (
        sale.status is SaleStatus.CHOOSING
        and sale.qr_token.exchanged_at is None
        and hmac.compare_digest(hash_qr_token_nonce(claims.nonce), sale.qr_token.nonce_hash)
    )


class CustomerSessionService:
    """Opens one customer session per QR exchange, and checks and describes sessions after it.

    The QR token is single-use (ADR 0022 decision 4): a reused, replaced, expired, forged or
    unknown token, and a sale no longer CHOOSING, all get the same calm 401, so nothing can be
    probed. A new exchange revokes the sale's earlier sessions. The session token is random
    (256 bits), returned once, and stored only as its hash.
    """

    def __init__(  # noqa: PLR0913 - a use case wired with its collaborators, by keyword
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        qr_token_signer: QrTokenSigner,
        clock: Clock,
        id_generator: IdGenerator,
        event_bus: DomainEventBus,
        sale_expiry: SaleExpiryStep,
        session_lifetime: timedelta,
        session_token_issuer: SessionTokenIssuer = issue_opaque_token,
    ) -> None:
        """Keeps the collaborators, the session lifetime and the source of session tokens."""
        self._unit_of_work_factory = unit_of_work_factory
        self._qr_token_signer = qr_token_signer
        self._clock = clock
        self._id_generator = id_generator
        self._event_bus = event_bus
        self._sale_expiry = sale_expiry
        self._session_access = CustomerSessionAccess(sale_expiry)
        self._session_lifetime = session_lifetime
        self._session_token_issuer = session_token_issuer

    def start(self, qr_token: str) -> StartedCustomerSession:
        """Exchanges the QR token for a new session; any refusal is CustomerQrTokenInvalidError.

        An overdue sale is expired first, and that expiry is kept before the refusal is raised.
        """
        try:
            claims = self._qr_token_signer.verify(qr_token)
        except QrTokenRejectedError as rejection:
            raise CustomerQrTokenInvalidError(INVALID_QR_CODE_DETAIL) from rejection
        issued_token = self._session_token_issuer()
        started_session: StartedCustomerSession | None = None
        with self._unit_of_work_factory() as unit_of_work:
            sale = unit_of_work.sales.find_by_id_for_update(claims.sale_id)
            if sale is None:
                raise CustomerQrTokenInvalidError(INVALID_QR_CODE_DETAIL)
            now = self._clock.now()
            current_sale = self._sale_expiry.expire_if_overdue(unit_of_work, sale, now)
            if _is_exchangeable(current_sale, claims):
                started_session = self._open_session(unit_of_work, current_sale, issued_token, now)
        if started_session is None:
            raise CustomerQrTokenInvalidError(INVALID_QR_CODE_DETAIL)
        return started_session

    def resolve(self, credentials: CustomerSessionCredentials) -> CustomerSession:
        """Gives the active session the token opens; 401 for a bad token, 404 for another id."""
        with self._unit_of_work_factory() as unit_of_work:
            return self._session_access.authenticate(unit_of_work, credentials, self._clock.now())

    def get_summary(self, credentials: CustomerSessionCredentials) -> CustomerSessionSummary:
        """Gives the session's C1 facts and the customer's own progress, never the token."""
        with self._unit_of_work_factory() as unit_of_work:
            opened = self._session_access.open_sale(unit_of_work, credentials, self._clock.now())
            session, sale = opened.session, opened.sale
            return CustomerSessionSummary(
                customer_session_id=session.id,
                session_code=sale.session_code.value,
                shop_name=find_shop_name(unit_of_work, sale),
                product_name=find_sale_product(unit_of_work, sale).name,
                price=sale.price,
                expires_at=session.expires_at,
                has_confirmed_budget=session.monthly_budget is not None,
                comfort_check_status=session.comfort_check_status,
                language=session.language,
                has_consented=unit_of_work.consent_records.find_for_sale(sale.id) is not None,
            )

    def _open_session(
        self,
        unit_of_work: UnitOfWork,
        sale: Sale,
        issued_token: IssuedOpaqueToken,
        now: datetime,
    ) -> StartedCustomerSession:
        """Marks the token exchanged, revokes earlier sessions and stores the new one."""
        unit_of_work.sales.update(sale.mark_qr_token_exchanged(now))
        for earlier_session in unit_of_work.customer_sessions.list_unrevoked_for_sale_for_update(
            sale.id
        ):
            unit_of_work.customer_sessions.update(earlier_session.revoke(now))
        session = CustomerSession.start(
            customer_session_id=self._id_generator.new_id(),
            sale_id=sale.id,
            token_hash=issued_token.token_hash,
            started_at=now,
            lifetime=self._session_lifetime,
        )
        unit_of_work.customer_sessions.add(session)
        self._event_bus.publish(
            CustomerSessionStarted(
                occurred_at=now, customer_session_id=session.id, sale_id=sale.id
            ),
            unit_of_work,
        )
        return StartedCustomerSession(
            customer_session_id=session.id,
            session_token=issued_token.token,
            session_code=sale.session_code.value,
            shop_name=find_shop_name(unit_of_work, sale),
            product_name=find_sale_product(unit_of_work, sale).name,
            price=sale.price,
            expires_at=session.expires_at,
        )
