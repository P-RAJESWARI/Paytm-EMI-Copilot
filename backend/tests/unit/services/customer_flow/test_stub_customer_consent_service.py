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
    InvalidPlanSelectionError,
    OfferNotFoundError,
    OtpExpiredError,
    OtpIncorrectError,
    OtpNotRequestedError,
    ShownPlanChangedError,
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


def build_command(  # noqa: PLR0913 - one override per field of the selection
    idempotency_key: str = FIRST_KEY,
    *,
    offer_id: str = NO_COST_OFFER_ID,
    one_time_code: str = STUB_CODE,
    product_id: str | None = None,
    down_payment_in_rupees: str = "0",
    shown_monthly_in_rupees: str = "3666.67",
    shown_total_in_rupees: str = "22000",
) -> GiveConsentCommand:
    """Builds a consent to no-cost 6 months on the 128 GB phone, as C9 showed it."""
    return GiveConsentCommand(
        idempotency_key=idempotency_key,
        offer_id=offer_id,
        one_time_code=one_time_code,
        product_id=product_id,
        down_payment=Money.from_rupees(down_payment_in_rupees),
        shown_monthly_installment=Money.from_rupees(shown_monthly_in_rupees),
        shown_total_payable=Money.from_rupees(shown_total_in_rupees),
    )


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
    consented_plan = recorded_consent.consented_plan
    snapshot = consented_plan.offer_snapshot
    assert snapshot.offer_id == NO_COST_OFFER_ID
    assert snapshot.regular_installment.to_paise() == 366_667
    assert snapshot.last_installment.to_paise() == 366_665
    assert snapshot.extra_in_total.is_zero
    assert consented_plan.price == Money.from_rupees("22000")
    assert consented_plan.financed_amount == Money.from_rupees("22000")
    assert consented_plan.down_payment.is_zero
    assert consented_plan.product_id == "stub-product-phone-128gb"
    assert consented_plan.product_name == "Example phone, 128 GB"
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
    assert receipt.consented_plan == recorded_consent.consented_plan
    assert receipt.reference == "EMI-2611-0042"
    assert receipt.phone_last_two_digits == "42"
    assert receipt.consented_at == recorded_consent.consented_at


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


def test_give_consent_command_fingerprint_follows_the_selection_never_the_key_or_code() -> None:
    """Keys and codes do not change it; another shown figure or down payment does."""
    fingerprint = build_command().calculate_request_fingerprint()
    assert build_command(SECOND_KEY).calculate_request_fingerprint() == fingerprint
    assert build_command(one_time_code="654321").calculate_request_fingerprint() == fingerprint
    assert build_command(shown_total_in_rupees="22001").calculate_request_fingerprint() != (
        fingerprint
    )
    assert build_command(down_payment_in_rupees="4000").calculate_request_fingerprint() != (
        fingerprint
    )


def test_give_consent_replay_with_another_code_gives_the_original(kit: CustomerFlowKit) -> None:
    """The code is not part of the request body's identity, so a retry with a typo replays."""
    credentials = prepare_for_consent(kit)
    first_consent = give_consent(kit, credentials, build_command())
    assert give_consent(kit, credentials, build_command(one_time_code="654321")) == first_consent


def test_give_consent_to_the_down_payment_option_stores_that_selection(
    kit: CustomerFlowKit,
) -> None:
    """₹4,000 down on no-cost 6 months: ₹18,000 financed, ₹3,000.00 x 6, price ₹22,000."""
    credentials = prepare_for_consent(kit)
    consented_plan = give_consent(
        kit,
        credentials,
        build_command(
            down_payment_in_rupees="4000",
            shown_monthly_in_rupees="3000",
            shown_total_in_rupees="18000",
        ),
    ).consented_plan
    assert consented_plan.down_payment == Money.from_rupees("4000")
    assert consented_plan.financed_amount == Money.from_rupees("18000")
    assert consented_plan.price == Money.from_rupees("22000")
    assert consented_plan.offer_snapshot.regular_installment.to_paise() == 300_000
    assert consented_plan.offer_snapshot.last_installment.to_paise() == 300_000
    assert consented_plan.product_id == "stub-product-phone-128gb"


def test_give_consent_to_the_cheaper_model_stores_that_product(kit: CustomerFlowKit) -> None:
    """The 64 GB phone at ₹18,000 on no-cost 6 months is stored with its id and name."""
    credentials = prepare_for_consent(kit)
    consented_plan = give_consent(
        kit,
        credentials,
        build_command(
            product_id="stub-product-phone-64gb",
            shown_monthly_in_rupees="3000",
            shown_total_in_rupees="18000",
        ),
    ).consented_plan
    assert consented_plan.product_id == "stub-product-phone-64gb"
    assert consented_plan.product_name == "Example phone, 64 GB"
    assert consented_plan.price == Money.from_rupees("18000")
    assert consented_plan.financed_amount == Money.from_rupees("18000")
    assert consented_plan.down_payment.is_zero


def test_give_consent_with_figures_that_differ_from_the_quote_raises(
    kit: CustomerFlowKit,
) -> None:
    """A shown monthly or total that the fresh quote does not match records nothing."""
    credentials = prepare_for_consent(kit)
    with pytest.raises(ShownPlanChangedError, match="show the plans again"):
        give_consent(kit, credentials, build_command(shown_monthly_in_rupees="3667"))
    with pytest.raises(ShownPlanChangedError):
        give_consent(kit, credentials, build_command(SECOND_KEY, shown_total_in_rupees="22002"))
    with pytest.raises(ConsentNotGivenError):
        kit.services.consent_service.get_receipt(credentials)


@pytest.mark.parametrize(
    ("offer_id", "down_payment_in_rupees"),
    [(NO_COST_OFFER_ID, "1234"), (NO_COST_OFFER_ID, "5000"), ("mock-offer-cardless-12m", "1000")],
    ids=["not-the-suggestion", "more-than-suggested", "plan-already-fits"],
)
def test_give_consent_with_a_down_payment_not_offered_raises(
    kit: CustomerFlowKit, offer_id: str, down_payment_in_rupees: str
) -> None:
    """Only zero or exactly the suggested down payment for that plan can be agreed to."""
    credentials = prepare_for_consent(kit)
    with pytest.raises(InvalidPlanSelectionError, match="down payment"):
        give_consent(
            kit,
            credentials,
            build_command(offer_id=offer_id, down_payment_in_rupees=down_payment_in_rupees),
        )


def test_give_consent_for_an_unknown_product_raises(kit: CustomerFlowKit) -> None:
    """Only the session's item and the offered cheaper model can be agreed to."""
    credentials = prepare_for_consent(kit)
    with pytest.raises(InvalidPlanSelectionError, match="product"):
        give_consent(kit, credentials, build_command(product_id="stub-product-other"))


def test_give_consent_to_the_item_by_its_explicit_product_id_is_accepted(
    kit: CustomerFlowKit,
) -> None:
    """Naming the session's own item is the same as leaving the product out."""
    credentials = prepare_for_consent(kit)
    consented_plan = give_consent(
        kit, credentials, build_command(product_id="stub-product-phone-128gb")
    ).consented_plan
    assert consented_plan.product_name == "Example phone, 128 GB"


def test_rescan_keeps_consent_and_the_old_key_replays_the_original(kit: CustomerFlowKit) -> None:
    """Consent is evidence: a re-scan keeps it, and a replay under the new token returns it."""
    first_credentials = prepare_for_consent(kit)
    first_consent = give_consent(kit, first_credentials, build_command())
    second_credentials = kit.start_standard_session()
    replayed_consent = give_consent(kit, second_credentials, build_command())
    assert replayed_consent.consent_id == first_consent.consent_id
    assert kit.services.consent_service.get_receipt(second_credentials).reference == (
        first_consent.reference
    )
    with pytest.raises(ConsentAlreadyGivenError):
        give_consent(kit, second_credentials, build_command(SECOND_KEY))
