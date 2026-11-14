"""STUB until Phase 3C: customer sessions held in memory, one store per application instance."""

import hmac
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType

from emi_copilot.domain.money import Money
from emi_copilot.services.customer_flow.customer_flow_types import RecordedConsent


@dataclass(frozen=True, slots=True)
class StubConsentRecord:
    """STUB until Phase 3C: one consent under its Idempotency-Key and request fingerprint."""

    idempotency_key: str
    request_fingerprint: str
    recorded_consent: RecordedConsent


@dataclass(frozen=True, slots=True)
class StubCustomerSession:
    """STUB until Phase 3C: one customer's progress; None means "not done yet".

    A re-scan of the QR replaces only the token and token_issued_at; the progress and the
    consent records are kept, because consent is append-only evidence (ADR 0021).
    """

    customer_session_id: str
    session_token: str
    session_code: str
    token_issued_at: datetime
    monthly_budget: Money | None = None
    has_comfort_check_consent: bool | None = None
    one_time_code_issued_at: datetime | None = None
    consent_records_by_key: Mapping[str, StubConsentRecord] = field(
        default_factory=lambda: MappingProxyType({})
    )

    @property
    def recorded_consent(self) -> RecordedConsent | None:
        """Gives the consent given in this session, whichever key recorded it, or None."""
        return next(
            (record.recorded_consent for record in self.consent_records_by_key.values()), None
        )


class StubCustomerSessionTable:
    """STUB until Phase 3C: the sessions, reachable only while the store's lock is held."""

    def __init__(self, sessions_by_id: dict[str, StubCustomerSession]) -> None:
        """Wraps the store's sessions for one locked block."""
        self._sessions_by_id = sessions_by_id

    def find(self, customer_session_id: str) -> StubCustomerSession | None:
        """Gives the session with the id, or None."""
        return self._sessions_by_id.get(customer_session_id)

    def find_by_token(self, session_token: str) -> StubCustomerSession | None:
        """Gives the session holding the token, comparing in constant time, or None."""
        presented_token = session_token.encode("utf-8")
        return next(
            (
                session
                for session in self._sessions_by_id.values()
                if hmac.compare_digest(session.session_token.encode("utf-8"), presented_token)
            ),
            None,
        )

    def save(self, session: StubCustomerSession) -> None:
        """Stores the session, replacing any earlier state under its id."""
        self._sessions_by_id[session.customer_session_id] = session


# Pattern: Repository (in-memory stub). Keeps session state out of the services; Phase 3C swaps
# it for database repositories inside a unit of work.
class StubCustomerSessionStore:
    """STUB until Phase 3C: sessions in memory, guarded by one lock; never a module global."""

    def __init__(self) -> None:
        """Starts empty with its own lock."""
        self._lock = threading.Lock()
        self._sessions_by_id: dict[str, StubCustomerSession] = {}

    @contextmanager
    def exclusive_access(self) -> Iterator[StubCustomerSessionTable]:
        """Holds the lock for one read-check-write, so two requests never interleave."""
        with self._lock:
            yield StubCustomerSessionTable(self._sessions_by_id)
