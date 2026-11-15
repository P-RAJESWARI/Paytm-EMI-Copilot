"""Wires the customer flow services on the shared fakes, with the design shop and its sale."""

from dataclasses import dataclass, field
from datetime import timedelta

from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.adapters.payment_gateway.mock_offer_catalogue import (
    MOCK_EARBUDS_PRODUCT_ID,
    MOCK_PHONE_64_GB_PRODUCT_ID,
    MOCK_PHONE_128_GB_PRODUCT_ID,
    quote_mock_offers,
)
from emi_copilot.core.opaque_token import IssuedOpaqueToken, hash_opaque_token
from emi_copilot.core.qr_token_signer import QrTokenClaims, QrTokenSigner, hash_qr_token_nonce
from emi_copilot.domain.comfort import FinancialProfile
from emi_copilot.domain.money import Money
from emi_copilot.services.customer.customer_choice_service import CustomerChoiceService
from emi_copilot.services.customer.customer_plan_service import CustomerPlanService
from emi_copilot.services.customer.customer_session_service import CustomerSessionService
from emi_copilot.services.customer.customer_session_types import (
    CustomerSessionCredentials,
    StartedCustomerSession,
)
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.plan_advice_service import PlanAdviceService
from emi_copilot.services.sale_expiry import SaleExpiryStep
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
STANDARD_PROFILE = FinancialProfile(
    monthly_inflow=Money.from_rupees(30000), existing_emis_per_month=Money.from_rupees(8000)
)
"""The design's customer: inflow ₹30,000, existing EMIs ₹8,000 (synthetic)."""


class SequentialSessionTokenIssuer:
    """Issues predictable session tokens, so a test can present the one it was given."""

    def __init__(self) -> None:
        """Starts counting at zero."""
        self._issued_count = 0

    def __call__(self) -> IssuedOpaqueToken:
        """Returns the next numbered token with its hash."""
        self._issued_count += 1
        token = f"synthetic-session-token-{self._issued_count:04d}"
        return IssuedOpaqueToken(token=token, token_hash=hash_opaque_token(token))


@dataclass
class RecordingFinancialProfilePort(FinancialProfilePort):
    """Gives the standard synthetic profile and records which sessions asked."""

    customer_session_ids: list[str] = field(default_factory=list)

    def get_financial_profile(self, customer_session_id: str) -> FinancialProfile:
        """Records the session id and gives the standard profile."""
        self.customer_session_ids.append(customer_session_id)
        return STANDARD_PROFILE


@dataclass
class CustomerServices:
    """The customer flow services and the doubles behind them."""

    sessions: CustomerSessionService
    choices: CustomerChoiceService
    plans: CustomerPlanService
    qr_token_signer: QrTokenSigner
    financial_profile_port: RecordingFinancialProfilePort
    sale_expiry: SaleExpiryStep
    offer_discovery: OfferDiscoveryService


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
    signer = QrTokenSigner(QR_SIGNING_KEY, kit.clock)
    profile_port = RecordingFinancialProfilePort()
    offer_discovery = OfferDiscoveryService(
        kit.payment_gateway, kit.unit_of_work_factory, kit.clock, kit.event_bus
    )
    return CustomerServices(
        sessions=CustomerSessionService(
            unit_of_work_factory=kit.unit_of_work_factory,
            qr_token_signer=signer,
            clock=kit.clock,
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
        qr_token_signer=signer,
        financial_profile_port=profile_port,
        sale_expiry=expiry,
        offer_discovery=offer_discovery,
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
