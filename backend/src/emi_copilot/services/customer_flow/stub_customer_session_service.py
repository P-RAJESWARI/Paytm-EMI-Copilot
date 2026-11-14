"""STUB until Phase 3C: starts a customer session from a QR and checks its session token."""

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
    ComfortCheckStatus,
    CustomerSessionCredentials,
    CustomerSessionSummary,
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


def _describe_comfort_check(has_comfort_check_consent: bool | None) -> ComfortCheckStatus | None:
    """Gives COMPLETED or SKIPPED for the customer's answer, or None before they answer."""
    if has_comfort_check_consent is None:
        return None
    if has_comfort_check_consent:
        return ComfortCheckStatus.COMPLETED
    return ComfortCheckStatus.SKIPPED


def require_confirmed_budget(session: StubCustomerSession) -> Money:
    """Gives the session's confirmed monthly budget; raises BudgetNotConfirmedError without one."""
    if session.monthly_budget is None:
        raise BudgetNotConfirmedError("Confirm a monthly budget before this step.")
    return session.monthly_budget


class StubCustomerSessionService:
    """STUB until Phase 3C: sample QR tokens open the sample sessions; tokens come from ids.

    Scanning a sample QR again issues a new token with a fresh lifetime and the earlier token
    stops working, but the progress and consent evidence are kept (ADR 0021). Phase 3C makes QR
    tokens single-use. Probing gets one answer: a token that opens no session is a 401, and a
    valid token used with any other session id is a 404, whether that id exists or not.
    """

    def __init__(
        self, store: StubCustomerSessionStore, clock: Clock, id_generator: IdGenerator
    ) -> None:
        """Keeps the session store, the clock and the id generator that issues tokens."""
        self._store = store
        self._clock = clock
        self._id_generator = id_generator

    def start_session(self, qr_token: str) -> StartedCustomerSession:
        """Opens or re-opens the QR's sample session with a new token; unknown QRs are a 401."""
        qr_code = STUB_QR_CODES_BY_TOKEN.get(qr_token)
        if qr_code is None:
            raise CustomerQrTokenInvalidError(
                "This QR code is not valid; ask the shop for a new QR."
            )
        session_token = self._id_generator.new_id()
        token_issued_at = self._clock.now()
        with self._store.exclusive_access() as sessions:
            existing_session = sessions.find(qr_code.customer_session_id)
            if existing_session is None:
                session = StubCustomerSession(
                    customer_session_id=qr_code.customer_session_id,
                    session_token=session_token,
                    session_code=qr_code.session_code,
                    token_issued_at=token_issued_at,
                )
            else:
                session = replace(
                    existing_session, session_token=session_token, token_issued_at=token_issued_at
                )
            sessions.save(session)
        return StartedCustomerSession(
            customer_session_id=session.customer_session_id,
            session_token=session.session_token,
            session_code=session.session_code,
            shop_name=STUB_SHOP_NAME,
            product_name=STUB_ITEM_PRODUCT_NAME,
            price=STUB_ITEM.price,
            expires_at=session.token_issued_at + STUB_SESSION_LIFETIME,
        )

    def authenticate(
        self, sessions: StubCustomerSessionTable, credentials: CustomerSessionCredentials
    ) -> StubCustomerSession:
        """Gives the session the token opens; call it while holding the store's lock.

        A token that opens no session, or an ended one, raises CustomerSessionTokenInvalidError.
        A valid token used with another session id raises CustomerSessionNotFoundError, the same
        answer whether that id exists or not, so ids cannot be probed.
        """
        session = sessions.find_by_token(credentials.session_token)
        if session is None:
            raise CustomerSessionTokenInvalidError(
                "This session link is not valid; ask the shop for a new QR."
            )
        if self._clock.now() >= session.token_issued_at + STUB_SESSION_LIFETIME:
            raise CustomerSessionTokenInvalidError(
                "This session has ended; ask the shop for a new QR."
            )
        if session.customer_session_id != credentials.customer_session_id:
            raise CustomerSessionNotFoundError("No customer session has this id.")
        return session

    def get_session_summary(
        self, credentials: CustomerSessionCredentials
    ) -> CustomerSessionSummary:
        """Gives the session's C1 facts and the customer's own progress, without the token."""
        with self._store.exclusive_access() as sessions:
            session = self.authenticate(sessions, credentials)
        return CustomerSessionSummary(
            customer_session_id=session.customer_session_id,
            session_code=session.session_code,
            shop_name=STUB_SHOP_NAME,
            product_name=STUB_ITEM_PRODUCT_NAME,
            price=STUB_ITEM.price,
            expires_at=session.token_issued_at + STUB_SESSION_LIFETIME,
            has_confirmed_budget=session.monthly_budget is not None,
            comfort_check_status=_describe_comfort_check(session.has_comfort_check_consent),
            has_consented=session.recorded_consent is not None,
        )

    def confirm_budget(
        self, credentials: CustomerSessionCredentials, monthly_budget: Money
    ) -> Money:
        """Stores the monthly budget the customer confirmed on C2 and gives it back."""
        require_valid_monthly_budget(monthly_budget)
        with self._store.exclusive_access() as sessions:
            session = self.authenticate(sessions, credentials)
            sessions.save(replace(session, monthly_budget=monthly_budget))
        return monthly_budget
