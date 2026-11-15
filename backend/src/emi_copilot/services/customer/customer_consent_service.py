"""CustomerConsentService: records consent as hash-chained evidence and agrees the sale's plan."""

from dataclasses import dataclass
from datetime import datetime, tzinfo

from emi_copilot.adapters.customer_contact.port import CustomerContactPort
from emi_copilot.core.clock import Clock
from emi_copilot.core.consent_reference_serial_generator import ConsentReferenceSerialGenerator
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.core.keyed_hasher import KeyedHasher
from emi_copilot.domain.catalogue import CatalogueProduct
from emi_copilot.domain.consent import (
    ConsentEvidence,
    ConsentIdempotency,
    ConsentPlanSnapshot,
    ConsentRecord,
    ConsentReference,
    CustomerPhoneNumber,
    OtpVerificationOutcome,
)
from emi_copilot.domain.customer_sessions import CustomerSession
from emi_copilot.domain.errors import (
    ConsentAlreadyGivenError,
    IdempotencyKeyReusedError,
    InvalidPlanSelectionError,
    OtpExpiredError,
    ShownPlanChangedError,
)
from emi_copilot.domain.events import ConsentRecorded
from emi_copilot.domain.sales import ChosenPlan, Sale
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork, UnitOfWorkFactory
from emi_copilot.services.customer.consent_otp_service import require_customer_phone_number
from emi_copilot.services.customer.consent_otp_verifier import (
    OTP_EXPIRED_DETAIL,
    ConsentOtpVerifier,
)
from emi_copilot.services.customer.consent_types import (
    COOLING_OFF_WORDING_VERSION,
    GiveConsentCommand,
)
from emi_copilot.services.customer.customer_session_access import (
    CustomerSessionAccess,
    OpenedCustomerSale,
    build_sale_offer_query,
    find_sale_product,
    require_confirmed_budget,
)
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.plan_advice_types import PricedOfferSource
from emi_copilot.services.sale_agreement_step import SaleAgreementStep
from emi_copilot.services.sale_expiry import SaleExpiryStep


@dataclass(frozen=True, slots=True)
class _VerifiedConsentRequest:
    """A request whose session, budget and code checked out, with the sale's product."""

    session: CustomerSession
    sale: Sale
    product: CatalogueProduct


@dataclass(frozen=True, slots=True)
class _QuotedConsent:
    """A verified request with its fresh quote, as shown, and the number the code went to."""

    request: _VerifiedConsentRequest
    chosen_plan: ChosenPlan
    phone_number: CustomerPhoneNumber


def find_consent_replay(
    unit_of_work: UnitOfWork, sale_id: str, command: GiveConsentCommand, request_fingerprint: str
) -> ConsentRecord | None:
    """Gives the sale's stored consent when this request repeats it; None when there is none.

    The same key with another body is IdempotencyKeyReusedError (422); consent under another
    key is ConsentAlreadyGivenError (409), because a sale has one consent.
    """
    stored_record = unit_of_work.consent_records.find_for_sale(sale_id)
    if stored_record is None:
        return None
    if stored_record.idempotency.idempotency_key != command.idempotency_key:
        raise ConsentAlreadyGivenError("Consent for this sale was already given.")
    if stored_record.idempotency.request_fingerprint != request_fingerprint:
        raise IdempotencyKeyReusedError(
            "The Idempotency-Key was already used with a different body."
        )
    return stored_record


def build_consent_recorded(record: ConsentRecord) -> ConsentRecorded:
    """Describes an appended record by its ids and chain position, never its evidence."""
    return ConsentRecorded(
        occurred_at=record.evidence.consented_at,
        consent_id=record.id,
        sale_id=record.evidence.sale_id,
        customer_session_id=record.evidence.customer_session_id,
        offer_id=record.evidence.plan_snapshot.chosen_plan.offer_id,
        chain_position=record.chain_position,
    )


class CustomerConsentService:
    """Turns the customer's C9 agreement into one consent record and a READY_TO_PAY sale.

    Order: replay check, session and budget, the code (a refusal is saved in its own committed
    transaction), a fresh quote outside any transaction, then one unit of work that locks the
    chain and the sale, agrees the plan (SaleAgreementStep), appends the record, marks the code
    used and announces ConsentRecorded. Only a plan on the session's item at the sale price can be
    agreed, exactly as shown (ADR 0022 decisions 1 and 8).
    """

    def __init__(  # noqa: PLR0913 - a use case wired with its collaborators, by keyword
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        id_generator: IdGenerator,
        event_bus: DomainEventBus,
        sale_expiry: SaleExpiryStep,
        offer_source: PricedOfferSource,
        customer_contact: CustomerContactPort,
        keyed_hasher: KeyedHasher,
        consent_reference_serial_generator: ConsentReferenceSerialGenerator,
        consent_time_zone: tzinfo,
    ) -> None:
        """Keeps the collaborators; the time zone gives the shop's day in the reference."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._id_generator = id_generator
        self._event_bus = event_bus
        self._session_access = CustomerSessionAccess(sale_expiry)
        self._sale_agreement = SaleAgreementStep(event_bus, sale_expiry)
        self._otp_verifier = ConsentOtpVerifier(keyed_hasher, event_bus)
        self._offer_source = offer_source
        self._customer_contact = customer_contact
        self._keyed_hasher = keyed_hasher
        self._serial_generator = consent_reference_serial_generator
        self._consent_time_zone = consent_time_zone

    def give_consent(
        self, credentials: CustomerSessionCredentials, command: GiveConsentCommand
    ) -> ConsentRecord:
        """Records consent once and gives the record; a replay of the same request gets it again."""
        request_fingerprint = command.calculate_request_fingerprint()
        checked = self._verify_request(credentials, command, request_fingerprint)
        if isinstance(checked, ConsentRecord):
            return checked
        quoted_consent = _QuotedConsent(
            request=checked,
            chosen_plan=self._quote_shown_plan(checked, command),
            phone_number=require_customer_phone_number(self._customer_contact, checked.sale.id),
        )
        return self._record_consent(credentials, command, request_fingerprint, quoted_consent)

    def _verify_request(
        self,
        credentials: CustomerSessionCredentials,
        command: GiveConsentCommand,
        request_fingerprint: str,
    ) -> ConsentRecord | _VerifiedConsentRequest:
        """Gives a replayed record, or the checked request; refusals are raised after commit."""
        with self._unit_of_work_factory() as unit_of_work:
            now = self._clock.now()
            session = self._session_access.authenticate(unit_of_work, credentials, now)
            replayed_record = find_consent_replay(
                unit_of_work, session.sale_id, command, request_fingerprint
            )
            if replayed_record is not None:
                return replayed_record
            opened = self._session_access.open_sale_of(unit_of_work, session, now)
            refusal = opened.find_choosing_refusal()
            if refusal is None:
                require_confirmed_budget(session)
                product = find_sale_product(unit_of_work, opened.sale)
                attempt = self._otp_verifier.check(unit_of_work, session.id, command.otp_code, now)
                if attempt.outcome is OtpVerificationOutcome.VERIFIED:
                    return _VerifiedConsentRequest(session, opened.sale, product)
                refusal = self._otp_verifier.record_refusal(unit_of_work, attempt, now)
        raise refusal

    def _quote_shown_plan(
        self, request: _VerifiedConsentRequest, command: GiveConsentCommand
    ) -> ChosenPlan:
        """Re-quotes the offer on the session's item at the sale price; it must match C9's."""
        priced_offer = next(
            (
                offer
                for offer in self._offer_source.discover_offers(
                    build_sale_offer_query(request.sale, request.product)
                )
                if offer.offer.offer_id == command.offer_id
            ),
            None,
        )
        if priced_offer is None:
            raise InvalidPlanSelectionError(
                "This plan is not offered for this item at its price; ask the shop."
            )
        chosen_plan = ChosenPlan.from_priced_offer(priced_offer)
        if (
            chosen_plan.monthly_installment != command.shown_monthly_installment
            or chosen_plan.total_payable != command.shown_total_payable
        ):
            raise ShownPlanChangedError("The plan figures changed; show the plans again.")
        return chosen_plan

    def _record_consent(
        self,
        credentials: CustomerSessionCredentials,
        command: GiveConsentCommand,
        request_fingerprint: str,
        quoted_consent: _QuotedConsent,
    ) -> ConsentRecord:
        """Locks the chain and the sale, agrees the plan and appends the record, in one go."""
        with self._unit_of_work_factory() as unit_of_work:
            now = self._clock.now()
            previous_record = unit_of_work.consent_records.find_latest_for_update()
            session = self._session_access.authenticate(unit_of_work, credentials, now)
            replayed_record = find_consent_replay(
                unit_of_work, session.sale_id, command, request_fingerprint
            )
            if replayed_record is not None:
                return replayed_record
            outcome = self._sale_agreement.agree(
                unit_of_work, session.sale_id, quoted_consent.chosen_plan, now
            )
            if outcome.refusal is not None:
                # The sale left CHOOSING (expired or agreed); its expiry commits before raising.
                refusal = (
                    OpenedCustomerSale(session, outcome.sale).find_choosing_refusal()
                    or outcome.refusal
                )
            else:
                return self._append_consent(
                    unit_of_work, previous_record, command, quoted_consent, now
                )
        raise refusal

    def _append_consent(
        self,
        unit_of_work: UnitOfWork,
        previous_record: ConsentRecord | None,
        command: GiveConsentCommand,
        quoted_consent: _QuotedConsent,
        now: datetime,
    ) -> ConsentRecord:
        """Checks the code again under the locks, then appends the record and marks the code used.

        A code spent or expired since the first check rolls the agreement back (OTP_EXPIRED).
        """
        attempt = self._otp_verifier.check(
            unit_of_work, quoted_consent.request.session.id, command.otp_code, now
        )
        if attempt.outcome is not OtpVerificationOutcome.VERIFIED:
            raise OtpExpiredError(OTP_EXPIRED_DETAIL)
        record = ConsentRecord.append_after(
            previous_record,
            self._build_evidence(command, quoted_consent, now),
            ConsentIdempotency(command.idempotency_key, command.calculate_request_fingerprint()),
        )
        unit_of_work.consent_records.append(record)
        unit_of_work.otp_challenges.update(attempt.challenge)
        self._event_bus.publish(build_consent_recorded(record), unit_of_work)
        return record

    def _build_evidence(
        self, command: GiveConsentCommand, quoted_consent: _QuotedConsent, now: datetime
    ) -> ConsentEvidence:
        """Freezes what was agreed: the plan as shown, the phone's digest, language and wording."""
        request, phone_number = quoted_consent.request, quoted_consent.phone_number
        return ConsentEvidence(
            consent_id=self._id_generator.new_id(),
            sale_id=request.sale.id,
            customer_session_id=request.session.id,
            consent_reference=ConsentReference.for_consent_day(
                now.astimezone(self._consent_time_zone).date(),
                self._serial_generator.new_serial_number(),
            ),
            plan_snapshot=ConsentPlanSnapshot(
                product_id=request.product.id,
                product_name=request.product.name,
                price=request.sale.price,
                chosen_plan=quoted_consent.chosen_plan,
            ),
            phone_last_two_digits=phone_number.last_two_digits,
            phone_hash=self._keyed_hasher.hash_customer_phone_number(phone_number.national_number),
            language=command.language,
            cooling_off_wording_version=COOLING_OFF_WORDING_VERSION,
            consented_at=now,
        )
