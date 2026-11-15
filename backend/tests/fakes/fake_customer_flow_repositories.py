"""In-memory customer session, OTP challenge and consent record repositories, like the real ones."""

from dataclasses import replace

from emi_copilot.domain.consent import ConsentRecord, OtpChallenge
from emi_copilot.domain.customer_sessions import CustomerSession
from emi_copilot.domain.errors import (
    ConsentAlreadyGivenError,
    ConsentRecordChainConflictError,
    CustomerSessionNotFoundError,
    InvalidCustomerSessionDataError,
    OtpNotRequestedError,
)


class FakeCustomerSessionRepository:
    """Holds sessions in a dict; enforces the unique id and token hash like the database."""

    def __init__(self, customer_sessions_by_id: dict[str, CustomerSession]) -> None:
        """Works on the unit of work's private copy of the sessions."""
        self._customer_sessions_by_id = customer_sessions_by_id

    def add(self, customer_session: CustomerSession) -> None:
        """Stores a new session; a duplicate id or token hash fails as in the database."""
        for stored in self._customer_sessions_by_id.values():
            if stored.id == customer_session.id or stored.token_hash == customer_session.token_hash:
                raise InvalidCustomerSessionDataError(
                    "A session with this id or token exists (fake)."
                )
        self._customer_sessions_by_id[customer_session.id] = customer_session

    def update(self, customer_session: CustomerSession) -> CustomerSession:
        """Saves only the mutable fields, as the real repository does."""
        stored = self._customer_sessions_by_id.get(customer_session.id)
        if stored is None:
            raise CustomerSessionNotFoundError("No such customer session (fake).")
        updated = replace(
            stored,
            monthly_budget=customer_session.monthly_budget,
            comfort_check_status=customer_session.comfort_check_status,
            language=customer_session.language,
            revoked_at=customer_session.revoked_at,
        )
        self._customer_sessions_by_id[customer_session.id] = updated
        return updated

    def find_by_token_hash(self, token_hash: str) -> CustomerSession | None:
        """Returns the session with this token hash, or None."""
        return next(
            (
                customer_session
                for customer_session in self._customer_sessions_by_id.values()
                if customer_session.token_hash == token_hash
            ),
            None,
        )

    def find_by_id_for_update(self, customer_session_id: str) -> CustomerSession | None:
        """Returns the session; a single-threaded fake needs no lock."""
        return self._customer_sessions_by_id.get(customer_session_id)

    def list_unrevoked_for_sale_for_update(self, sale_id: str) -> tuple[CustomerSession, ...]:
        """Lists the sale's sessions not yet revoked, oldest first, as the real query does."""
        return tuple(
            sorted(
                (
                    customer_session
                    for customer_session in self._customer_sessions_by_id.values()
                    if customer_session.sale_id == sale_id and customer_session.revoked_at is None
                ),
                key=lambda customer_session: (customer_session.created_at, customer_session.id),
            )
        )


class FakeOtpChallengeRepository:
    """Holds challenges in a dict and finds a session's latest like the real query."""

    def __init__(self, otp_challenges_by_id: dict[str, OtpChallenge]) -> None:
        """Works on the unit of work's private copy of the challenges."""
        self._otp_challenges_by_id = otp_challenges_by_id

    def add(self, otp_challenge: OtpChallenge) -> None:
        """Stores a new challenge."""
        self._otp_challenges_by_id[otp_challenge.id] = otp_challenge

    def update(self, otp_challenge: OtpChallenge) -> OtpChallenge:
        """Saves only the attempts left and the verification moment."""
        stored = self._otp_challenges_by_id.get(otp_challenge.id)
        if stored is None:
            raise OtpNotRequestedError("No such one-time code challenge (fake).")
        updated = replace(
            stored,
            attempts_remaining=otp_challenge.attempts_remaining,
            verified_at=otp_challenge.verified_at,
        )
        self._otp_challenges_by_id[otp_challenge.id] = updated
        return updated

    def find_latest_for_session_for_update(self, customer_session_id: str) -> OtpChallenge | None:
        """Returns the session's newest challenge by issue moment, then id."""
        return max(
            (
                otp_challenge
                for otp_challenge in self._otp_challenges_by_id.values()
                if otp_challenge.customer_session_id == customer_session_id
            ),
            key=lambda otp_challenge: (otp_challenge.created_at, otp_challenge.id),
            default=None,
        )


class FakeConsentRecordRepository:
    """Appends records to a list; enforces one consent per sale and an unforked chain."""

    def __init__(self, consent_records: list[ConsentRecord]) -> None:
        """Works on the unit of work's private copy of the chain."""
        self._consent_records = consent_records

    def find_latest_for_update(self) -> ConsentRecord | None:
        """Returns the chain head; a single-threaded fake needs no lock."""
        return max(self._consent_records, key=lambda record: record.chain_position, default=None)

    def append(self, consent_record: ConsentRecord) -> None:
        """Appends one record; a second consent or a taken chain place fails as in the database."""
        for stored in self._consent_records:
            if stored.evidence.sale_id == consent_record.evidence.sale_id:
                raise ConsentAlreadyGivenError("This sale already has a consent record (fake).")
            if (
                stored.chain_position == consent_record.chain_position
                or stored.previous_record_hash == consent_record.previous_record_hash
            ):
                raise ConsentRecordChainConflictError("This chain place is taken (fake).")
        self._consent_records.append(consent_record)

    def list_in_order(self) -> tuple[ConsentRecord, ...]:
        """Returns the chain ordered by position."""
        return tuple(sorted(self._consent_records, key=lambda record: record.chain_position))

    def find_for_sale(self, sale_id: str) -> ConsentRecord | None:
        """Returns the sale's consent record, or None."""
        return next(
            (record for record in self._consent_records if record.evidence.sale_id == sale_id),
            None,
        )
