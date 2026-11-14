"""STUB until Phase 3C: the one-time code (C9), consent as evidence, and the receipt (C10)."""

import hmac
from dataclasses import replace
from types import MappingProxyType

from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.domain.errors import (
    ConsentAlreadyGivenError,
    ConsentNotGivenError,
    IdempotencyKeyReusedError,
    OfferNotFoundError,
    OtpExpiredError,
    OtpIncorrectError,
    OtpNotRequestedError,
)
from emi_copilot.domain.payments import PricedEmiOffer
from emi_copilot.services.customer_flow.customer_flow_types import (
    CoolingOffNoticeStatus,
    CustomerReceipt,
    CustomerSessionCredentials,
    GiveConsentCommand,
    OtpChallenge,
    ReceiptStatus,
    RecordedConsent,
)
from emi_copilot.services.customer_flow.stub_customer_session_service import (
    StubCustomerSessionService,
    require_confirmed_budget,
)
from emi_copilot.services.customer_flow.stub_customer_session_store import (
    StubConsentRecord,
    StubCustomerSession,
    StubCustomerSessionStore,
)
from emi_copilot.services.customer_flow.stub_design_sample import (
    STUB_ITEM,
    STUB_ONE_TIME_CODE,
    STUB_ONE_TIME_CODE_LIFETIME,
    STUB_ONE_TIME_CODE_RESEND_DELAY,
    STUB_PHONE_LAST_TWO_DIGITS,
    STUB_RECEIPT_REFERENCE,
)
from emi_copilot.services.plan_advice_types import PricedOfferSource


class StubCustomerConsentService:
    """STUB until Phase 3C: consent with a fixed one-time code, kept in memory as evidence.

    Consent stores the exact plan snapshot shown, once per session. The same Idempotency-Key and
    body replay the stored result. There is no payment link: the merchant takes payment on Paytm.
    Phase 3C moves consent to the append-only, hash-chained consent_record table.
    """

    def __init__(
        self,
        store: StubCustomerSessionStore,
        session_service: StubCustomerSessionService,
        offer_source: PricedOfferSource,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        """Keeps the store, the session checker, the offer source, the clock and id generator."""
        self._store = store
        self._session_service = session_service
        self._offer_source = offer_source
        self._clock = clock
        self._id_generator = id_generator

    def request_one_time_code(self, credentials: CustomerSessionCredentials) -> OtpChallenge:
        """Issues the stub one-time code; asking again restarts its lifetime."""
        issued_at = self._clock.now()
        with self._store.exclusive_access() as sessions:
            session = self._session_service.authenticate(sessions, credentials)
            sessions.save(replace(session, one_time_code_issued_at=issued_at))
        return OtpChallenge(
            phone_last_two_digits=STUB_PHONE_LAST_TWO_DIGITS,
            expires_at=issued_at + STUB_ONE_TIME_CODE_LIFETIME,
            resend_available_at=issued_at + STUB_ONE_TIME_CODE_RESEND_DELAY,
        )

    def give_consent(
        self, credentials: CustomerSessionCredentials, command: GiveConsentCommand
    ) -> RecordedConsent:
        """Records consent to the chosen plan once; a replay of the same request gives it again.

        The lock is held across the offer quote, which is the in-memory Mock in Phase 3A.
        """
        request_fingerprint = command.calculate_request_fingerprint()
        with self._store.exclusive_access() as sessions:
            session = self._session_service.authenticate(sessions, credentials)
            stored_record = session.consent_records_by_key.get(command.idempotency_key)
            if stored_record is not None:
                if stored_record.request_fingerprint != request_fingerprint:
                    raise IdempotencyKeyReusedError(
                        "The Idempotency-Key was already used with a different body."
                    )
                return stored_record.recorded_consent
            if session.recorded_consent is not None:
                raise ConsentAlreadyGivenError("Consent was already given in this session.")
            self._require_valid_one_time_code(session, command.one_time_code)
            recorded_consent = self._record_consent(self._find_quoted_plan(command.offer_id))
            consent_record = StubConsentRecord(
                command.idempotency_key, request_fingerprint, recorded_consent
            )
            sessions.save(
                replace(
                    session,
                    consent_records_by_key=MappingProxyType(
                        {command.idempotency_key: consent_record}
                    ),
                )
            )
        return recorded_consent

    def get_receipt(self, credentials: CustomerSessionCredentials) -> CustomerReceipt:
        """Gives the C10 receipt; before consent it raises ConsentNotGivenError."""
        with self._store.exclusive_access() as sessions:
            session = self._session_service.authenticate(sessions, credentials)
        recorded_consent = session.recorded_consent
        if recorded_consent is None:
            raise ConsentNotGivenError("There is no receipt until the plan is agreed.")
        return CustomerReceipt(
            status=ReceiptStatus.READY_TO_PAY,
            reference=recorded_consent.reference,
            phone_last_two_digits=STUB_PHONE_LAST_TWO_DIGITS,
            consented_at=recorded_consent.consented_at,
            cooling_off_notice_status=CoolingOffNoticeStatus.PLACEHOLDER,
            offer_snapshot=recorded_consent.offer_snapshot,
            price=recorded_consent.price,
        )

    def _require_valid_one_time_code(
        self, session: StubCustomerSession, one_time_code: str
    ) -> None:
        """Needs a budget, a requested code within its lifetime, and a matching code."""
        require_confirmed_budget(session)
        if session.one_time_code_issued_at is None:
            raise OtpNotRequestedError("Request a one-time code before agreeing.")
        if self._clock.now() >= session.one_time_code_issued_at + STUB_ONE_TIME_CODE_LIFETIME:
            raise OtpExpiredError("This code has expired; request a new code.")
        if not hmac.compare_digest(one_time_code.encode("utf-8"), STUB_ONE_TIME_CODE.encode()):
            raise OtpIncorrectError("This code does not match; check it or request a new code.")

    def _find_quoted_plan(self, offer_id: str) -> PricedEmiOffer:
        """Re-quotes the sample item and gives the chosen plan; OfferNotFoundError if absent."""
        for priced_offer in self._offer_source.discover_offers(STUB_ITEM):
            if priced_offer.offer.offer_id == offer_id:
                return priced_offer
        raise OfferNotFoundError("The chosen offer is not quoted for this item and price.")

    def _record_consent(self, priced_offer: PricedEmiOffer) -> RecordedConsent:
        """Freezes the plan shown as evidence, with a new consent id and the consent time."""
        return RecordedConsent(
            consent_id=self._id_generator.new_id(),
            reference=STUB_RECEIPT_REFERENCE,
            consented_at=self._clock.now(),
            offer_snapshot=priced_offer.to_offer_snapshot(),
            price=priced_offer.schedule.principal,
        )
