"""StubCustomerConsentService: one-time code, consent as evidence, idempotency and receipt."""

import threading
from datetime import timedelta

import pytest

from emi_copilot.domain.errors import (
    BudgetNotConfirmedError,
    ConsentAlreadyGivenError,
    ConsentNotGivenError,
    DomainError,
    IdempotencyKeyReusedError,
    OfferNotFoundError,
    OtpExpiredError,
    OtpIncorrectError,
    OtpNotRequestedError,
)
from emi_copilot.domain.money import Money
from emi_copilot.services.customer_flow.customer_flow_types import (
    CoolingOffNoticeStatus,
    CustomerSessionCredentials,
    GiveConsentCommand,
    ReceiptStatus,
    RecordedConsent,
)
from tests.payment_builders import CREATED_AT
from tests.unit.services.customer_flow.conftest import CustomerFlowKit

STUB_CODE = "123456"
FIRST_KEY = "stub-consent-key-0001"
SECOND_KEY = "stub-consent-key-0002"
NO_COST_OFFER_ID = "mock-offer-no-cost-6m"


def build_command(
    idempotency_key: str = FIRST_KEY,
    offer_id: str = NO_COST_OFFER_ID,
    one_time_code: str = STUB_CODE,
) -> GiveConsentCommand:
    """Builds a consent to no-cost 6 months with the stub code."""
    return GiveConsentCommand(idempotency_key, offer_id, one_time_code)


def prepare_for_consent(kit: CustomerFlowKit) -> CustomerSessionCredentials:
    """Starts the standard session, confirms ₹3,000 and requests the one-time code."""
    credentials = kit.start_standard_session()
    kit.confirm_budget(credentials)
    kit.services.consent_service.request_one_time_code(credentials)
    return credentials


def give_consent(
    kit: CustomerFlowKit, credentials: CustomerSessionCredentials, command: GiveConsentCommand
) -> RecordedConsent:
    """Gives consent through the service under test."""
    return kit.services.consent_service.give_consent(credentials, command)


def test_request_one_time_code_gives_phone_ending_lifetime_and_resend_time(
    kit: CustomerFlowKit,
) -> None:
    """C9: sent to the phone ending 42, valid 5 minutes, resend after 30 seconds."""
    credentials = kit.start_standard_session()
    challenge = kit.services.consent_service.request_one_time_code(credentials)
    assert challenge.phone_last_two_digits == "42"
    assert challenge.expires_at == CREATED_AT + timedelta(minutes=5)
    assert challenge.resend_available_at == CREATED_AT + timedelta(seconds=30)


def test_give_consent_freezes_the_exact_plan_shown(kit: CustomerFlowKit) -> None:
    """Consent stores plan A as evidence: 5 x ₹3,666.67 then ₹3,666.65, nothing extra."""
    recorded_consent = give_consent(kit, prepare_for_consent(kit), build_command())
    snapshot = recorded_consent.offer_snapshot
    assert snapshot.offer_id == NO_COST_OFFER_ID
    assert snapshot.regular_installment.to_paise() == 366_667
    assert snapshot.last_installment.to_paise() == 366_665
    assert snapshot.extra_in_total.is_zero
    assert recorded_consent.price == Money.from_rupees("22000")
    assert recorded_consent.reference == "EMI-2611-0042"
    assert recorded_consent.consented_at == CREATED_AT


def test_give_consent_same_key_and_body_replays_the_stored_result(kit: CustomerFlowKit) -> None:
    """A retried request gives the original consent, even after the code would have expired."""
    credentials = prepare_for_consent(kit)
    first_consent = give_consent(kit, credentials, build_command())
    kit.clock.advance(timedelta(minutes=10))
    assert give_consent(kit, credentials, build_command()) == first_consent


def test_give_consent_same_key_with_another_body_raises(kit: CustomerFlowKit) -> None:
    """A key reused for a different plan is refused with 422 IDEMPOTENCY_KEY_REUSED."""
    credentials = prepare_for_consent(kit)
    give_consent(kit, credentials, build_command())
    with pytest.raises(IdempotencyKeyReusedError):
        give_consent(kit, credentials, build_command(offer_id="mock-offer-cardless-12m"))


def test_give_consent_again_under_a_new_key_raises_already_given(kit: CustomerFlowKit) -> None:
    """Consent happens once per session."""
    credentials = prepare_for_consent(kit)
    give_consent(kit, credentials, build_command())
    with pytest.raises(ConsentAlreadyGivenError):
        give_consent(kit, credentials, build_command(SECOND_KEY))


def test_give_consent_without_a_budget_raises(kit: CustomerFlowKit) -> None:
    """Consent needs the confirmed budget."""
    credentials = kit.start_standard_session()
    with pytest.raises(BudgetNotConfirmedError):
        give_consent(kit, credentials, build_command())


def test_give_consent_without_requesting_a_code_raises(kit: CustomerFlowKit) -> None:
    """Consent needs a requested one-time code."""
    credentials = kit.start_standard_session()
    kit.confirm_budget(credentials)
    with pytest.raises(OtpNotRequestedError):
        give_consent(kit, credentials, build_command())


def test_give_consent_with_a_wrong_code_raises_and_allows_a_retry(kit: CustomerFlowKit) -> None:
    """A wrong code is calm and blames no one; the right code then works."""
    credentials = prepare_for_consent(kit)
    with pytest.raises(OtpIncorrectError, match="request a new code"):
        give_consent(kit, credentials, build_command(one_time_code="654321"))
    assert give_consent(kit, credentials, build_command()).reference == "EMI-2611-0042"


def test_give_consent_after_five_minutes_raises_expired(kit: CustomerFlowKit) -> None:
    """The code lasts 5 minutes; a new request starts a new lifetime."""
    credentials = prepare_for_consent(kit)
    kit.clock.advance(timedelta(minutes=5))
    with pytest.raises(OtpExpiredError):
        give_consent(kit, credentials, build_command())
    kit.services.consent_service.request_one_time_code(credentials)
    assert give_consent(kit, credentials, build_command()).consented_at == kit.clock.now()


def test_give_consent_to_an_unquoted_offer_raises(kit: CustomerFlowKit) -> None:
    """Only a plan quoted for the item can be agreed to."""
    credentials = prepare_for_consent(kit)
    with pytest.raises(OfferNotFoundError):
        give_consent(kit, credentials, build_command(offer_id="offer-not-quoted"))


def test_get_receipt_before_consent_raises(kit: CustomerFlowKit) -> None:
    """There is no receipt until the plan is agreed."""
    credentials = kit.start_standard_session()
    with pytest.raises(ConsentNotGivenError):
        kit.services.consent_service.get_receipt(credentials)


def test_get_receipt_after_consent_is_ready_to_pay_with_a_placeholder_note(
    kit: CustomerFlowKit,
) -> None:
    """C10 hand-off: the merchant now takes payment; the cooling-off wording is a placeholder."""
    credentials = prepare_for_consent(kit)
    recorded_consent = give_consent(kit, credentials, build_command())
    receipt = kit.services.consent_service.get_receipt(credentials)
    assert receipt.status is ReceiptStatus.READY_TO_PAY
    assert receipt.cooling_off_notice_status is CoolingOffNoticeStatus.PLACEHOLDER
    assert receipt.offer_snapshot == recorded_consent.offer_snapshot
    assert receipt.reference == "EMI-2611-0042"
    assert receipt.phone_last_two_digits == "42"
    assert receipt.consented_at == recorded_consent.consented_at
    assert receipt.price == Money.from_rupees("22000")


def test_give_consent_racing_under_two_keys_records_exactly_one(kit: CustomerFlowKit) -> None:
    """The store's lock makes the check and the write one step, so only one consent wins."""
    credentials = prepare_for_consent(kit)
    outcomes: list[str] = []

    def consent_under(idempotency_key: str) -> None:
        """Tries to consent and notes the outcome."""
        try:
            give_consent(kit, credentials, build_command(idempotency_key))
            outcomes.append("recorded")
        except DomainError as error:
            outcomes.append(error.code)

    threads = [
        threading.Thread(target=consent_under, args=(key,)) for key in (FIRST_KEY, SECOND_KEY)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["CONSENT_ALREADY_GIVEN", "recorded"]


def test_give_consent_command_fingerprint_ignores_the_key_and_follows_the_body() -> None:
    """Two keys with one body share a fingerprint; another code changes it."""
    assert build_command().calculate_request_fingerprint() == (
        build_command(SECOND_KEY).calculate_request_fingerprint()
    )
    assert build_command().calculate_request_fingerprint() != (
        build_command(one_time_code="654321").calculate_request_fingerprint()
    )
