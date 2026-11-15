"""Wires the customer flow services on the shared fakes, with the design shop and its sale."""

from dataclasses import dataclass
from datetime import timedelta
from zoneinfo import ZoneInfo

from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_EARBUDS_PRODUCT_ID,
    MOCK_PHONE_64_GB_PRODUCT_ID,
    MOCK_PHONE_128_GB_PRODUCT_ID,
    quote_mock_offers,
)
from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.core.keyed_hasher import KeyedHasher
from emi_copilot.core.qr_token_signer import QrTokenClaims, QrTokenSigner, hash_qr_token_nonce
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.money import Money
from emi_copilot.services.ai.shown_explanation_cache import ShownExplanationCache
from emi_copilot.services.customer.consent_otp_service import ConsentOtpService
from emi_copilot.services.customer.consent_types import GiveConsentCommand
from emi_copilot.services.customer.customer_choice_service import CustomerChoiceService
from emi_copilot.services.customer.customer_consent_service import CustomerConsentService
from emi_copilot.services.customer.customer_explanation_service import CustomerExplanationService
from emi_copilot.services.customer.customer_plan_service import CustomerPlanService
from emi_copilot.services.customer.customer_receipt_service import CustomerReceiptService
from emi_copilot.services.customer.customer_session_service import CustomerSessionService
from emi_copilot.services.customer.customer_session_types import (
    CustomerSessionCredentials,
    StartedCustomerSession,
)
from emi_copilot.services.customer.session_plan_finder import SessionPlanFinder
from emi_copilot.services.customer.template_explanation_service import (
    TemplateExplanationService,
)
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.plan_advice_service import PlanAdviceService
from emi_copilot.services.sale_expiry import SaleExpiryStep
from tests.fakes.fake_customer_flow_ports import (
    OTP_CODE,
    FakeCustomerContact,
    FixedConsentOtpCodeGenerator,
    FixedConsentReferenceSerialGenerator,
    RecordingConsentOtpSender,
    RecordingFinancialProfilePort,
    SequentialSessionTokenIssuer,
)
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.merchant_builders import build_catalogue_product, build_merchant
from tests.sale_builders import (
    CHOOSING_LIFETIME,
    QR_TOKEN_LIFETIME,
    SALE_ID,
    SALE_STARTED_AT,
    build_qr_token_state,
    build_sale,
)
from tests.unit.services.conftest import ServiceTestKit

QR_SIGNING_KEY = b"synthetic-customer-test-qr-signing-key-01"  # pragma: allowlist secret
QR_NONCE = "synthetic-qr-nonce-0001"
SESSION_LIFETIME = timedelta(minutes=30)
SALE_DEADLINE_GAP = timedelta(minutes=15)
"""How long before the sale's deadline start_session_near_the_sale_deadline opens a session."""
PHONE_64_GB_PRODUCT_ID = "01JCPRODUCT000000000000064"
EARBUDS_PRODUCT_ID = "01JCPRODUCT000000000000099"
PHONE_HASH_KEY = b"synthetic-customer-test-phone-hash-key-01"  # pragma: allowlist secret
OTP_LIFETIME = timedelta(minutes=5)
OTP_RESEND_WAIT = timedelta(seconds=30)
OTP_MAXIMUM_ATTEMPTS = 3
INDIA_TIME_ZONE = ZoneInfo("Asia/Kolkata")
NO_COST_OFFER_ID = "mock-offer-no-cost-6m"


@dataclass
class CustomerServices:
    """The customer flow services and the doubles behind them."""

    sessions: CustomerSessionService
    choices: CustomerChoiceService
    plans: CustomerPlanService
    otp: ConsentOtpService
    consent: CustomerConsentService
    receipt: CustomerReceiptService
    explanation: CustomerExplanationService
    qr_token_signer: QrTokenSigner
    financial_profile_port: RecordingFinancialProfilePort
    customer_contact: FakeCustomerContact
    otp_sender: RecordingConsentOtpSender
    keyed_hasher: KeyedHasher


def quote_like_the_mock_gateway(payment_gateway: FakePaymentGateway) -> None:
    """Makes the fake gateway answer each query with the Mock's demo plans for that product."""

    def quote_last_query() -> None:
        """Replaces the scripted offers with the Mock's quote for the query just recorded."""
        query = payment_gateway.discover_offers_calls[-1]
        payment_gateway.offers = quote_mock_offers(query.price, query.product_id)

    payment_gateway.before_discover_offers = quote_last_query


def store_design_shop(kit: ServiceTestKit) -> None:
    """Stores the shop, its 128 GB and 64 GB phones and earbuds, and a CHOOSING 128 GB sale."""
    merchant = build_merchant(display_name="Ravi Electronics")
    kit.database.merchants_by_id[merchant.id] = merchant
    for product in (
        build_catalogue_product(gateway_product_id=MOCK_PHONE_128_GB_PRODUCT_ID),
        build_catalogue_product(
            id=PHONE_64_GB_PRODUCT_ID,
            name="Example phone, 64 GB",
            list_price=Money.from_rupees(18000),
            gateway_product_id=MOCK_PHONE_64_GB_PRODUCT_ID,
        ),
        build_catalogue_product(
            id=EARBUDS_PRODUCT_ID,
            name="Example earbuds",
            list_price=Money.from_rupees(2499),
            gateway_product_id=MOCK_EARBUDS_PRODUCT_ID,
            gateway_category_id="category-synthetic-audio",
        ),
    ):
        kit.database.products_by_id[product.id] = product
    kit.database.sales_by_id[SALE_ID] = build_sale(
        qr_token=build_qr_token_state(nonce_hash=hash_qr_token_nonce(QR_NONCE))
    )
    quote_like_the_mock_gateway(kit.payment_gateway)


def sign_qr_token(
    signer: QrTokenSigner,
    nonce: str = QR_NONCE,
    sale_id: str = SALE_ID,
    lifetime: timedelta = QR_TOKEN_LIFETIME,
) -> str:
    """Signs the token the merchant's QR would carry for the sale, valid from the sale's start."""
    return signer.sign(
        QrTokenClaims(sale_id=sale_id, nonce=nonce, expires_at=SALE_STARTED_AT + lifetime)
    )


def credentials_of(started_session: StartedCustomerSession) -> CustomerSessionCredentials:
    """Gives the credentials a phone presents after the exchange."""
    return CustomerSessionCredentials(
        started_session.customer_session_id, started_session.session_token
    )


def wire_customer_services(kit: ServiceTestKit) -> CustomerServices:
    """Builds the customer services on the kit's fakes as the composition root will."""
    expiry = SaleExpiryStep(kit.event_bus, CHOOSING_LIFETIME)
    profile_port = RecordingFinancialProfilePort()
    offer_discovery = OfferDiscoveryService(
        kit.payment_gateway, kit.unit_of_work_factory, kit.clock, kit.event_bus
    )
    customer_contact = FakeCustomerContact()
    otp_sender = RecordingConsentOtpSender()
    keyed_hasher = KeyedHasher(PHONE_HASH_KEY)
    return CustomerServices(
        sessions=CustomerSessionService(
            unit_of_work_factory=kit.unit_of_work_factory,
            clock=kit.clock,
            qr_token_signer=QrTokenSigner(QR_SIGNING_KEY, kit.clock),
            id_generator=kit.id_generator,
            event_bus=kit.event_bus,
            sale_expiry=expiry,
            session_lifetime=SESSION_LIFETIME,
            session_token_issuer=SequentialSessionTokenIssuer(),
        ),
        choices=CustomerChoiceService(
            unit_of_work_factory=kit.unit_of_work_factory,
            clock=kit.clock,
            event_bus=kit.event_bus,
            sale_expiry=expiry,
            financial_profile_port=profile_port,
            are_financial_profiles_synthetic=True,
        ),
        plans=CustomerPlanService(
            unit_of_work_factory=kit.unit_of_work_factory,
            clock=kit.clock,
            event_bus=kit.event_bus,
            sale_expiry=expiry,
            plan_advice_service=PlanAdviceService(offer_discovery),
            financial_profile_port=profile_port,
        ),
        otp=ConsentOtpService(
            unit_of_work_factory=kit.unit_of_work_factory,
            clock=kit.clock,
            id_generator=kit.id_generator,
            sale_expiry=expiry,
            customer_contact=customer_contact,
            code_generator=FixedConsentOtpCodeGenerator(),
            code_sender=otp_sender,
            keyed_hasher=keyed_hasher,
            otp_lifetime=OTP_LIFETIME,
            otp_resend_wait=OTP_RESEND_WAIT,
            otp_maximum_attempts=OTP_MAXIMUM_ATTEMPTS,
        ),
        consent=CustomerConsentService(
            unit_of_work_factory=kit.unit_of_work_factory,
            clock=kit.clock,
            id_generator=kit.id_generator,
            event_bus=kit.event_bus,
            sale_expiry=expiry,
            offer_source=offer_discovery,
            customer_contact=customer_contact,
            keyed_hasher=keyed_hasher,
            consent_reference_serial_generator=FixedConsentReferenceSerialGenerator(),
            consent_time_zone=INDIA_TIME_ZONE,
        ),
        receipt=CustomerReceiptService(kit.unit_of_work_factory, kit.clock, expiry),
        explanation=CustomerExplanationService(
            SessionPlanFinder(kit.unit_of_work_factory, kit.clock, expiry, offer_discovery),
            TemplateExplanationService(format_paise_as_whole_rupees),
            ShownExplanationCache(kit.clock),
            kit.id_generator,
        ),
        qr_token_signer=QrTokenSigner(QR_SIGNING_KEY, kit.clock),
        financial_profile_port=profile_port,
        customer_contact=customer_contact,
        otp_sender=otp_sender,
        keyed_hasher=keyed_hasher,
    )


def start_session_near_the_sale_deadline(
    services: CustomerServices, kit: ServiceTestKit
) -> CustomerSessionCredentials:
    """Exchanges a QR 45 minutes into the sale, so the sale's hour ends inside the session.

    Advancing the clock by SALE_DEADLINE_GAP afterwards reaches the sale's deadline exactly.
    """
    kit.clock.advance(CHOOSING_LIFETIME - SALE_DEADLINE_GAP)
    return credentials_of(
        services.sessions.start(sign_qr_token(services.qr_token_signer, lifetime=CHOOSING_LIFETIME))
    )


def build_plan_a_consent_command(**overrides: object) -> GiveConsentCommand:
    """Consent to design plan A as C9 shows it: ₹3,666.67 a month, ₹22,000 in total, in English."""
    fields: dict[str, object] = {
        "idempotency_key": "consent-key-0001",
        "offer_id": NO_COST_OFFER_ID,
        "shown_monthly_installment": Money.from_rupees("3666.67"),
        "shown_total_payable": Money.from_rupees(22000),
        "otp_code": OTP_CODE,
        "has_agreed_to_plan": True,
        "language": CustomerLanguage.ENGLISH,
    }
    fields.update(overrides)
    return GiveConsentCommand(**fields)  # type: ignore[arg-type]


def prepare_for_consent(
    services: CustomerServices, credentials: CustomerSessionCredentials
) -> None:
    """Confirms a ₹3,000 budget, skips the comfort check and requests the code (C2, C3, C9)."""
    services.choices.confirm_budget(credentials, Money.from_rupees(3000))
    services.choices.record_comfort_check_choice(credentials, has_customer_consented=False)
    services.otp.request_otp(credentials)
