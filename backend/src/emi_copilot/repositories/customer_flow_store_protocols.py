"""What the customer flow needs from a unit of work: sessions, one-time codes and consents.

Kept apart from unit_of_work_protocol.py, whose UnitOfWork uses them, so each file stays small.
"""

from typing import Protocol

from emi_copilot.domain.consent import ConsentRecord, OtpChallenge
from emi_copilot.domain.customer_sessions import CustomerSession


class CustomerSessionStore(Protocol):
    """Adds, updates and finds customer sessions inside one transaction."""

    def add(self, customer_session: CustomerSession) -> None:
        """Inserts a new session."""
        ...

    def update(self, customer_session: CustomerSession) -> CustomerSession:
        """Saves budget, comfort choice, language and revocation; returns the stored session."""
        ...

    def find_by_token_hash(self, token_hash: str) -> CustomerSession | None:
        """Returns the session whose token hashes to this value, or None."""
        ...

    def find_by_id_for_update(self, customer_session_id: str) -> CustomerSession | None:
        """Returns the session with this id, locked until the transaction ends, or None."""
        ...

    def list_unrevoked_for_sale_for_update(self, sale_id: str) -> tuple[CustomerSession, ...]:
        """Lists the sale's sessions not yet revoked, oldest first, rows locked."""
        ...


class OtpChallengeStore(Protocol):
    """Adds, updates and finds one-time code challenges inside one transaction."""

    def add(self, otp_challenge: OtpChallenge) -> None:
        """Inserts a new challenge."""
        ...

    def update(self, otp_challenge: OtpChallenge) -> OtpChallenge:
        """Saves the attempts left and the verification moment; returns the stored challenge."""
        ...

    def find_latest_for_session_for_update(self, customer_session_id: str) -> OtpChallenge | None:
        """Returns the session's most recently issued challenge, locked, or None."""
        ...


class ConsentRecordStore(Protocol):
    """Appends and reads consent records; there is deliberately no update or delete."""

    def find_latest_for_update(self) -> ConsentRecord | None:
        """Takes the chain lock until the transaction ends, then gives the chain head, or None."""
        ...

    def append(self, consent_record: ConsentRecord) -> None:
        """Inserts one record; a second consent for a sale or a chain fork raises a typed error."""
        ...

    def list_in_order(self) -> tuple[ConsentRecord, ...]:
        """Returns the whole chain from the first record."""
        ...

    def find_for_sale(self, sale_id: str) -> ConsentRecord | None:
        """Returns the sale's consent record, or None."""
        ...
