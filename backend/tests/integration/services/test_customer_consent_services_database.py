"""Integration: consent with OTP, the receipt and the template explanation on PostgreSQL."""

from datetime import timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.consent import verify_consent_record_chain
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.errors import (
    CustomerSessionTokenInvalidError,
    IdempotencyKeyReusedError,
    InvalidPlanSelectionError,
    OtpExpiredError,
    OtpIncorrectError,
    OtpResendNotYetAvailableError,
    ShownPlanChangedError,
)
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import AuditEventType, PaymentAttemptStatus
from emi_copilot.domain.sales import SalePaymentOutcome, SaleStatus
from emi_copilot.services.customer.consent_types import ReceiptStatus
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from tests.fixed_clock import FixedClock
from tests.integration.services.customer_flow_database_wiring import (
    DESIGN_SALE_IDS,
    DatabaseCustomerServices,
    nonce_for,
    wire_database_customer_services,
)
from tests.payment_builders import build_payment_attempt
from tests.sale_builders import CHOOSING_LIFETIME
from tests.unit.services.customer.customer_service_wiring import (
    build_plan_a_consent_command,
    credentials_of,
    sign_qr_token,
)

pytestmark = pytest.mark.integration

SALE_ID = DESIGN_SALE_IDS[0]
WRONG_CODE = "000000"


@pytest.fixture
def services(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> DatabaseCustomerServices:
    """Stores the design shop and its sales, then wires the customer services."""
    return wire_database_customer_services(session_factory, fixed_clock)


def ready_for_consent(
    services: DatabaseCustomerServices,
    sale_id: str = SALE_ID,
    qr_lifetime: timedelta = timedelta(minutes=15),
) -> CustomerSessionCredentials:
    """Exchanges the sale's QR, confirms ₹3,000, skips the comfort check and requests a code."""
    credentials = credentials_of(
        services.sessions.start(
            sign_qr_token(
                services.qr_token_signer,
                nonce=nonce_for(sale_id),
                sale_id=sale_id,
                lifetime=qr_lifetime,
            )
        )
    )
    services.choices.confirm_budget(credentials, Money.from_rupees(3000))
    services.choices.record_comfort_check_choice(credentials, has_customer_consented=False)
    services.otp.request_otp(credentials)
    return credentials


def assert_nothing_recorded(services: DatabaseCustomerServices) -> None:
    """No consent row exists and the sale is still CHOOSING."""
    assert services.read_consent_chain() == ()
    stored_sale = services.read_sale(SALE_ID)
    assert stored_sale is not None
    assert stored_sale.status is SaleStatus.CHOOSING


def test_consent_writes_exactly_one_record_and_moves_the_sale_together(
    services: DatabaseCustomerServices,
) -> None:
    """One consent row, READY_TO_PAY with plan A, AGREED in the funnel, audited, code used."""
    credentials = ready_for_consent(services)
    record = services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert services.read_consent_chain() == (record,)
    stored_sale = services.read_sale(SALE_ID)
    assert stored_sale is not None
    assert stored_sale.status is SaleStatus.READY_TO_PAY
    assert stored_sale.chosen_plan == record.evidence.plan_snapshot.chosen_plan
    assert FunnelStage.AGREED in [event.stage for event in services.read_funnel_events(SALE_ID)]
    assert AuditEventType.SALE_STATUS_CHANGED in services.read_audit_types("sale", SALE_ID)
    assert services.read_audit_types("consent_record", record.id) == [
        AuditEventType.CONSENT_RECORDED
    ]
    challenge = services.read_latest_challenge(credentials.customer_session_id)
    assert challenge is not None
    assert challenge.verified_at is not None


def test_consent_when_the_sale_step_fails_writes_no_record(
    services: DatabaseCustomerServices,
) -> None:
    """The sale expires during the quote: the expiry is stored, and no consent row exists."""
    services.clock.advance(timedelta(minutes=45))
    credentials = ready_for_consent(services, qr_lifetime=CHOOSING_LIFETIME)
    services.hooked_offer_source.after_quote = lambda: services.clock.advance(timedelta(minutes=15))
    with pytest.raises(CustomerSessionTokenInvalidError):
        services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert services.read_consent_chain() == ()
    stored_sale = services.read_sale(SALE_ID)
    assert stored_sale is not None
    assert stored_sale.status is SaleStatus.EXPIRED


def test_consents_on_several_sales_form_one_intact_chain(
    services: DatabaseCustomerServices,
) -> None:
    """Each record links to the one before it, across sales."""
    for sale_id in DESIGN_SALE_IDS:
        services.consent.give_consent(
            ready_for_consent(services, sale_id), build_plan_a_consent_command()
        )
    chain = services.read_consent_chain()
    assert [record.chain_position for record in chain] == [1, 2]
    assert chain[1].previous_record_hash == chain[0].record_hash
    assert verify_consent_record_chain(chain).is_intact


def test_two_wrong_codes_are_stored_then_the_right_one_is_accepted(
    services: DatabaseCustomerServices,
) -> None:
    """Each miss commits its used attempt, even though the request fails."""
    credentials = ready_for_consent(services)
    for expected_attempts_left in (2, 1):
        with pytest.raises(OtpIncorrectError) as wrong_code:
            services.consent.give_consent(
                credentials, build_plan_a_consent_command(otp_code=WRONG_CODE)
            )
        assert wrong_code.value.attempts_remaining == expected_attempts_left
    challenge = services.read_latest_challenge(credentials.customer_session_id)
    assert challenge is not None
    assert challenge.attempts_remaining == 1
    services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert len(services.read_consent_chain()) == 1


def test_three_wrong_codes_spend_the_code(services: DatabaseCustomerServices) -> None:
    """The third miss answers OTP_EXPIRED and the right code no longer works."""
    credentials = ready_for_consent(services)
    for _ in range(2):
        with pytest.raises(OtpIncorrectError):
            services.consent.give_consent(
                credentials, build_plan_a_consent_command(otp_code=WRONG_CODE)
            )
    with pytest.raises(OtpExpiredError):
        services.consent.give_consent(
            credentials, build_plan_a_consent_command(otp_code=WRONG_CODE)
        )
    with pytest.raises(OtpExpiredError):
        services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert_nothing_recorded(services)


def test_requesting_a_new_code_too_early_is_refused(services: DatabaseCustomerServices) -> None:
    """The resend wait is 30 seconds (429 OTP_RESEND_NOT_YET_AVAILABLE)."""
    credentials = ready_for_consent(services)
    with pytest.raises(OtpResendNotYetAvailableError) as refusal:
        services.otp.request_otp(credentials)
    assert refusal.value.retry_after_in_seconds == 30


def test_consent_replay_gives_the_stored_record_and_another_body_is_refused(
    services: DatabaseCustomerServices,
) -> None:
    """Same key and figures replay from consent_record.idempotency_key; other figures are 422."""
    credentials = ready_for_consent(services)
    record = services.consent.give_consent(credentials, build_plan_a_consent_command())
    assert services.consent.give_consent(credentials, build_plan_a_consent_command()) == record
    with pytest.raises(IdempotencyKeyReusedError):
        services.consent.give_consent(
            credentials,
            build_plan_a_consent_command(shown_monthly_installment=Money.from_rupees(3850)),
        )
    assert len(services.read_consent_chain()) == 1


@pytest.mark.parametrize(
    ("offer_id", "monthly_in_paise", "total_in_paise", "expected_error"),
    [
        ("mock-offer-no-cost-6m", 366_667, 2_310_000, ShownPlanChangedError),
        ("mock-offer-no-cost-6m", 300_000, 1_800_000, ShownPlanChangedError),
        ("mock-offer-of-another-product", 300_000, 1_800_000, InvalidPlanSelectionError),
    ],
    ids=["changed-total", "cheaper-model-figures", "offer-not-on-this-item"],
)
def test_consent_to_anything_but_a_plan_on_this_item_as_shown_writes_nothing(
    services: DatabaseCustomerServices,
    offer_id: str,
    monthly_in_paise: int,
    total_in_paise: int,
    expected_error: type[Exception],
) -> None:
    """Only the session's item at the sale price, exactly as shown, can be agreed."""
    credentials = ready_for_consent(services)
    with pytest.raises(expected_error):
        services.consent.give_consent(
            credentials,
            build_plan_a_consent_command(
                offer_id=offer_id,
                shown_monthly_installment=Money.from_paise(monthly_in_paise),
                shown_total_payable=Money.from_paise(total_in_paise),
            ),
        )
    assert_nothing_recorded(services)


def test_receipt_follows_the_sale_from_hand_off_to_paid(
    services: DatabaseCustomerServices,
) -> None:
    """READY_TO_PAY, then PAYMENT_PENDING once a link exists, then PAID; never "declined"."""
    credentials = ready_for_consent(services)
    record = services.consent.give_consent(
        credentials, build_plan_a_consent_command(language=CustomerLanguage.TAMIL)
    )
    receipt = services.receipt.get_receipt(credentials)
    assert (receipt.status, receipt.consent_record) == (ReceiptStatus.READY_TO_PAY, record)
    assert receipt.consent_record.evidence.language is CustomerLanguage.TAMIL
    with services.unit_of_work_factory() as unit_of_work:
        unit_of_work.payment_attempts.add(
            build_payment_attempt(1, status=PaymentAttemptStatus.LINK_CREATED, sale_id=SALE_ID)
        )
    assert services.receipt.get_receipt(credentials).status is ReceiptStatus.PAYMENT_PENDING
    with services.unit_of_work_factory() as unit_of_work:
        sale = unit_of_work.sales.find_by_id_for_update(SALE_ID)
        assert sale is not None
        paid_sale, _ = sale.apply_payment_outcome(SalePaymentOutcome.PAID, services.clock.now())
        unit_of_work.sales.update(paid_sale)
    assert services.receipt.get_receipt(credentials).status is ReceiptStatus.PAID


def test_explanation_numbers_match_the_quoted_plan(services: DatabaseCustomerServices) -> None:
    """The Mock's card plan on ₹22,000: ₹3,850 a month and ₹1,100 extra, in both languages."""
    credentials = ready_for_consent(services)
    for language in CustomerLanguage:
        explanation = services.explanation.explain_for_session(
            credentials, "mock-offer-card-6m", language
        )
        assert [highlight.amount for highlight in explanation.highlighted_amounts] == [
            Money.from_rupees(3850),
            Money.from_rupees(1100),
        ]
        assert "₹3,850" in explanation.text
        assert "₹1,100" in explanation.text
