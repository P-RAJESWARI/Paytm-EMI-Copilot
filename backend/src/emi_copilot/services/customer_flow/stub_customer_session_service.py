"""STUB until Phase 3C: starts a customer session from a QR and checks its session token."""

import hmac
from dataclasses import replace

from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.domain.errors import (
    BudgetNotConfirmedError,
    CustomerQrTokenInvalidError,
    CustomerSessionNotFoundError,
    CustomerSessionTokenInvalidError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.ranking import require_valid_monthly_budget
from emi_copilot.services.customer_flow.customer_flow_types import (
    CustomerSessionCredentials,
    StartedCustomerSession,
)
from emi_copilot.services.customer_flow.stub_customer_session_store import (
    StubCustomerSession,
    StubCustomerSessionStore,
    StubCustomerSessionTable,
)
from emi_copilot.services.customer_flow.stub_design_sample import (
    STUB_ITEM,
    STUB_ITEM_PRODUCT_NAME,
    STUB_QR_CODES_BY_TOKEN,
    STUB_SESSION_LIFETIME,
    STUB_SHOP_NAME,
)


def require_confirmed_budget(session: StubCustomerSession) -> Money:
    """Gives the session's confirmed monthly budget; raises BudgetNotConfirmedError without one."""
    if session.monthly_budget is None:
        raise BudgetNotConfirmedError("Confirm a monthly budget before this step.")
    return session.monthly_budget


class StubCustomerSessionService:
    """STUB until Phase 3C: sample QR tokens open the sample sessions; tokens come from ids.

    Scanning a sample QR again starts its sample session afresh with a new token, so the demo can
    be repeated; the earlier token stops working. Phase 3C makes QR tokens single-use.
    """

    def __init__(
        self, store: StubCustomerSessionStore, clock: Clock, id_generator: IdGenerator
    ) -> None:
        """Keeps the session store, the clock and the id generator that issues tokens."""
        self._store = store
        self._clock = clock
        self._id_generator = id_generator

    def start_session(self, qr_token: str) -> StartedCustomerSession:
        """Opens the QR's sample session; an unknown QR token raises CustomerQrTokenInvalidError."""
        qr_code = STUB_QR_CODES_BY_TOKEN.get(qr_token)
        if qr_code is None:
            raise CustomerQrTokenInvalidError(
                "This QR code is not valid; ask the shop for a new QR."
            )
        session = StubCustomerSession(
            customer_session_id=qr_code.customer_session_id,
            session_token=self._id_generator.new_id(),
            session_code=qr_code.session_code,
            started_at=self._clock.now(),
        )
        with self._store.exclusive_access() as sessions:
            sessions.save(session)
        return StartedCustomerSession(
            customer_session_id=session.customer_session_id,
            session_token=session.session_token,
            session_code=session.session_code,
            shop_name=STUB_SHOP_NAME,
            product_name=STUB_ITEM_PRODUCT_NAME,
            price=STUB_ITEM.price,
            expires_at=session.started_at + STUB_SESSION_LIFETIME,
        )

    def authenticate(
        self, sessions: StubCustomerSessionTable, credentials: CustomerSessionCredentials
    ) -> StubCustomerSession:
        """Gives the session the token opens; call it while holding the store's lock.

        An unknown id raises CustomerSessionNotFoundError; a wrong token or an ended session
        raises CustomerSessionTokenInvalidError.
        """
        session = sessions.find(credentials.customer_session_id)
        if session is None:
            raise CustomerSessionNotFoundError("No customer session has this id.")
        if not hmac.compare_digest(
            session.session_token.encode("utf-8"), credentials.session_token.encode("utf-8")
        ):
            raise CustomerSessionTokenInvalidError(
                "This session link is not valid; ask the shop for a new QR."
            )
        if self._clock.now() >= session.started_at + STUB_SESSION_LIFETIME:
            raise CustomerSessionTokenInvalidError(
                "This session has ended; ask the shop for a new QR."
            )
        return session

    def confirm_budget(
        self, credentials: CustomerSessionCredentials, monthly_budget: Money
    ) -> Money:
        """Stores the monthly budget the customer confirmed on C2 and gives it back."""
        require_valid_monthly_budget(monthly_budget)
        with self._store.exclusive_access() as sessions:
            session = self.authenticate(sessions, credentials)
            sessions.save(replace(session, monthly_budget=monthly_budget))
        return monthly_budget
