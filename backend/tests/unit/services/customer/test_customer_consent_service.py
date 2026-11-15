"""CustomerConsentService: one hash-chained record and READY_TO_PAY together, or nothing."""

from dataclasses import replace

import pytest

from emi_copilot.domain.consent import (
    ConsentPlanSnapshot,
    ConsentReference,
    verify_consent_record_chain,
)
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.errors import (
    ConsentAlreadyGivenError,
    CustomerContactUnavailableError,
    CustomerSessionTokenInvalidError,
    IdempotencyKeyReusedError,
    InvalidConsentDataError,
    InvalidPlanSelectionError,
    OtpExpiredError,
    OtpIncorrectError,
    OtpNotRequestedError,
    ShownPlanChangedError,
)
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import AuditEventType, EmiType
from emi_copilot.domain.sales import ChosenPlan, SaleStatus
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from tests.payment_builders import CREATED_AT
from tests.sale_builders import PRODUCT_ID, SALE_ID, build_no_cost_chosen_plan
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.customer.customer_service_wiring import (
    OTP_LIFETIME,
    SALE_DEADLINE_GAP,
    CustomerServices,
    build_plan_a_consent_command,
    credentials_of,
    prepare_for_consent,
    sign_qr_token,
    start_session_near_the_sale_deadline,
    store_design_shop,
    wire_customer_services,
)

PLAN_A = ChosenPlan(
    offer_id="mock-offer-no-cost-6m",
    plan_kind=EmiType.NO_COST,
    lender_label="Brand",
    tenure_in_months=6,
    monthly_installment=Money.from_rupees("3666.67"),
    extra_in_total=Money.from_paise(0),
    total_payable=Money.from_rupees(22000),
)


@pytest.fixture
def services(kit: ServiceTestKit) -> CustomerServices:
    """Stores the design shop and its CHOOSING sale, then wires the customer services."""
    store_design_shop(kit)
    return wire_customer_services(kit)


@pytest.fixture
def credentials(services: CustomerServices) -> CustomerSessionCredentials:
    """Exchanges the QR, confirms ₹3,000, skips the comfort check and requests a code."""
    credentials = credentials_of(services.sessions.start(sign_qr_token(services.qr_token_signer)))
    prepare_for_consent(services, credentials)
    return credentials


def assert_nothing_recorded(kit: ServiceTestKit) -> None:
    """No consent row, the sale still CHOOSING, the code not used."""
    assert kit.database.consent_records == []
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.CHOOSING
    assert all(
        challenge.verified_at is None for challenge in kit.database.otp_challenges_by_id.values()
    )


def test_give_consent_writes_one_record_and_moves_the_sale_to_ready_to_pay(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """The record holds plan A as shown; the sale agrees the same plan; the code is used."""
    record = services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert kit.database.consent_records == [record]
    evidence = record.evidence
    assert evidence.plan_snapshot == ConsentPlanSnapshot(
        product_id=PRODUCT_ID,
        product_name="Example phone, 128 GB",
        price=Money.from_rupees(22000),
        chosen_plan=PLAN_A,
    )
    assert evidence.consent_reference == ConsentReference("EMI-1411-0042")
    assert evidence.phone_last_two_digits == "42"
    assert evidence.phone_hash == services.keyed_hasher.hash_customer_phone_number("9000000042")
    assert (evidence.language, evidence.cooling_off_wording_version) == (
        CustomerLanguage.ENGLISH,
        "PLACEHOLDER",
    )
    assert evidence.consented_at == CREATED_AT
    stored_sale = kit.database.sales_by_id[SALE_ID]
    assert (stored_sale.status, stored_sale.chosen_plan) == (SaleStatus.READY_TO_PAY, PLAN_A)
    (challenge,) = kit.database.otp_challenges_by_id.values()
    assert challenge.verified_at == CREATED_AT
    assert verify_consent_record_chain(kit.database.consent_records).is_intact


def test_give_consent_announces_the_agreement_for_audit_and_the_funnel(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """READY_TO_PAY reaches the funnel (AGREED) and audit, with CONSENT_RECORDED."""
    services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert kit.audit_event_types()[-2:] == [
        AuditEventType.SALE_STATUS_CHANGED,
        AuditEventType.CONSENT_RECORDED,
    ]
    assert FunnelStage.AGREED in [event.stage for event in kit.database.funnel_events]


def test_give_consent_after_two_wrong_codes_then_the_right_one_succeeds(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Two tries left, then one, then the right code is accepted; each miss is audited."""
    attempts_left = []
    for _ in range(2):
        with pytest.raises(OtpIncorrectError) as wrong_code:
            services.consent.give_consent(
                credentials, build_plan_a_consent_command(otp_code="000000")
            )
        attempts_left.append(wrong_code.value.attempts_remaining)
    assert attempts_left == [2, 1]
    services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert kit.audit_event_types().count(AuditEventType.OTP_VERIFICATION_FAILED) == 2
    assert len(kit.database.consent_records) == 1


def test_give_consent_third_wrong_code_spends_it_and_the_right_one_then_expires(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """After three misses the code answers OTP_EXPIRED, never a lockout; nothing is recorded."""
    for _ in range(2):
        with pytest.raises(OtpIncorrectError):
            services.consent.give_consent(
                credentials, build_plan_a_consent_command(otp_code="000000")
            )
    with pytest.raises(OtpExpiredError):
        services.consent.give_consent(credentials, build_plan_a_consent_command(otp_code="000000"))
    with pytest.raises(OtpExpiredError):
        services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert_nothing_recorded(kit)


def test_give_consent_after_the_code_lifetime_is_expired(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """A code is valid for 5 minutes."""
    kit.clock.advance(OTP_LIFETIME)
    with pytest.raises(OtpExpiredError):
        services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert_nothing_recorded(kit)


def test_give_consent_without_a_requested_code_is_refused(services: CustomerServices) -> None:
    """Consent needs a code sent to the customer's phone first."""
    credentials = credentials_of(services.sessions.start(sign_qr_token(services.qr_token_signer)))
    services.choices.confirm_budget(credentials, Money.from_rupees(3000))
    with pytest.raises(OtpNotRequestedError):
        services.consent.give_consent(credentials, build_plan_a_consent_command())


def test_give_consent_replayed_with_the_same_key_and_figures_gives_the_same_record(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Same key, same offer and figures (even another code) is the same request."""
    first_record = services.consent.give_consent(credentials, build_plan_a_consent_command())
    replayed_record = services.consent.give_consent(
        credentials, build_plan_a_consent_command(otp_code="999999")
    )
    assert replayed_record == first_record
    assert len(kit.database.consent_records) == 1


def test_give_consent_with_a_used_key_and_another_body_is_refused(
    services: CustomerServices, credentials: CustomerSessionCredentials
) -> None:
    """Same key, other figures: 422 IDEMPOTENCY_KEY_REUSED."""
    services.consent.give_consent(credentials, build_plan_a_consent_command())
    with pytest.raises(IdempotencyKeyReusedError):
        services.consent.give_consent(
            credentials,
            build_plan_a_consent_command(shown_total_payable=Money.from_rupees(23100)),
        )


def test_give_consent_a_second_time_under_another_key_is_a_conflict(
    services: CustomerServices, credentials: CustomerSessionCredentials
) -> None:
    """A sale has one consent."""
    services.consent.give_consent(credentials, build_plan_a_consent_command())
    with pytest.raises(ConsentAlreadyGivenError):
        services.consent.give_consent(
            credentials, build_plan_a_consent_command(idempotency_key="consent-key-0002")
        )


@pytest.mark.parametrize(
    ("monthly_in_paise", "total_in_paise"),
    [(366_666, 2_200_000), (366_667, 2_200_001), (300_000, 1_800_000)],
    ids=["monthly-changed", "total-changed", "cheaper-model-figures-on-the-same-offer-id"],
)
def test_give_consent_with_figures_that_differ_from_a_fresh_quote_writes_nothing(
    services: CustomerServices,
    kit: ServiceTestKit,
    credentials: CustomerSessionCredentials,
    monthly_in_paise: int,
    total_in_paise: int,
) -> None:
    """409 SHOWN_PLAN_CHANGED: the plans are shown again; nothing is recorded or moved."""
    with pytest.raises(ShownPlanChangedError):
        services.consent.give_consent(
            credentials,
            build_plan_a_consent_command(
                shown_monthly_installment=Money.from_paise(monthly_in_paise),
                shown_total_payable=Money.from_paise(total_in_paise),
            ),
        )
    assert_nothing_recorded(kit)


def test_give_consent_to_an_offer_not_quoted_for_the_sessions_item_is_refused(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Only plans on the session's item at the sale price can be agreed (ADR 0022 decision 1)."""
    with pytest.raises(InvalidPlanSelectionError):
        services.consent.give_consent(
            credentials, build_plan_a_consent_command(offer_id="offer-for-another-product")
        )
    assert_nothing_recorded(kit)


def test_give_consent_without_a_known_phone_number_is_refused(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Evidence needs the phone's digest; without a number nothing is recorded."""
    services.customer_contact.phone_number = None
    with pytest.raises(CustomerContactUnavailableError):
        services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert_nothing_recorded(kit)


def test_give_consent_on_a_sale_agreed_without_consent_is_a_conflict(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """A sale the Mock customer simulator already agreed cannot get a second agreement."""
    sale = kit.database.sales_by_id[SALE_ID]
    kit.database.sales_by_id[SALE_ID] = sale.agree_to_plan(
        build_no_cost_chosen_plan(), sale.started_at
    )
    with pytest.raises(ConsentAlreadyGivenError):
        services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert kit.database.consent_records == []


def test_give_consent_when_the_sale_expires_during_the_quote_writes_no_record(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """The sale step refuses an expired sale; its expiry commits and no consent row exists."""
    credentials = start_session_near_the_sale_deadline(services, kit)
    prepare_for_consent(services, credentials)
    quote_like_the_mock = kit.payment_gateway.before_discover_offers

    def quote_then_pass_the_deadline() -> None:
        """Quotes as the Mock would, while the sale's hour runs out."""
        assert quote_like_the_mock is not None
        quote_like_the_mock()
        kit.clock.advance(SALE_DEADLINE_GAP)

    kit.payment_gateway.before_discover_offers = quote_then_pass_the_deadline
    with pytest.raises(CustomerSessionTokenInvalidError):
        services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert kit.database.consent_records == []
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.EXPIRED


def test_give_consent_when_the_code_is_spent_during_the_quote_rolls_the_agreement_back(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """The code is checked again under the locks; a failure there undoes the sale move too."""
    quote_like_the_mock = kit.payment_gateway.before_discover_offers

    def quote_then_spend_the_code() -> None:
        """Quotes as the Mock would, while another request uses the last attempt."""
        assert quote_like_the_mock is not None
        quote_like_the_mock()
        (challenge,) = kit.database.otp_challenges_by_id.values()
        kit.database.otp_challenges_by_id[challenge.id] = replace(challenge, attempts_remaining=0)

    kit.payment_gateway.before_discover_offers = quote_then_spend_the_code
    with pytest.raises(OtpExpiredError):
        services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert kit.database.consent_records == []
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.CHOOSING


def test_give_consent_recorded_by_a_parallel_request_during_the_quote_is_replayed(
    services: CustomerServices, kit: ServiceTestKit, credentials: CustomerSessionCredentials
) -> None:
    """Two taps with one key: the second finds the first's record under the chain lock."""
    quote_like_the_mock = kit.payment_gateway.before_discover_offers
    parallel_records = []

    def quote_while_the_first_tap_records() -> None:
        """Quotes as the Mock would; the first tap's consent lands meanwhile."""
        assert quote_like_the_mock is not None
        kit.payment_gateway.before_discover_offers = quote_like_the_mock
        quote_like_the_mock()
        parallel_records.append(
            services.consent.give_consent(credentials, build_plan_a_consent_command())
        )

    kit.payment_gateway.before_discover_offers = quote_while_the_first_tap_records
    replayed_record = services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert [replayed_record] == parallel_records == kit.database.consent_records


def test_consent_command_needs_the_agreement_and_keeps_the_code_out_of_the_fingerprint() -> None:
    """No "I agree", no consent; the code changes neither the fingerprint nor the repr."""
    with pytest.raises(InvalidConsentDataError):
        build_plan_a_consent_command(has_agreed_to_plan=False)
    command = build_plan_a_consent_command()
    other_code_command = build_plan_a_consent_command(otp_code="654321")
    assert command.calculate_request_fingerprint() == (
        other_code_command.calculate_request_fingerprint()
    )
    assert "123456" not in repr(command)
