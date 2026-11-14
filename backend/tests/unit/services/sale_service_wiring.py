"""Wires every sale service on the shared fakes, as the composition root will."""

from dataclasses import dataclass
from datetime import timedelta
from zoneinfo import ZoneInfo

from emi_copilot.core.qr_token_signer import QrTokenSigner
from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.services.customer_qr_link_issuer import CustomerQrLinkIssuer
from emi_copilot.services.get_sale_service import GetSaleService
from emi_copilot.services.issue_qr_token_service import IssueQrTokenService
from emi_copilot.services.list_counter_sales_service import ListCounterSalesService
from emi_copilot.services.mark_sale_ready_to_pay_service import MarkSaleReadyToPayService
from emi_copilot.services.offer_discovery_service import OfferDiscoveryService
from emi_copilot.services.sale_expiry import SaleExpiryStep
from emi_copilot.services.start_sale_service import StartSaleService
from tests.fakes.lowest_free_session_code_generator import LowestFreeSessionCodeGenerator
from tests.merchant_builders import MERCHANT_ID, OTHER_MERCHANT_ID, PAIRED_AT
from tests.unit.services.conftest import ServiceTestKit

QR_SIGNING_KEY = b"synthetic-service-test-qr-signing-key-0001"  # pragma: allowlist secret
CUSTOMER_WEB_BASE_URL = "https://customer.example.test"
QR_TOKEN_LIFETIME = timedelta(minutes=15)
CHOOSING_LIFETIME = timedelta(hours=1)
INDIA_TIME_ZONE = ZoneInfo("Asia/Kolkata")


def build_principal(merchant_id: str = MERCHANT_ID) -> MerchantPrincipal:
    """A signed-in counter device of the given shop."""
    return MerchantPrincipal(
        merchant_id=merchant_id,
        shop_code="SHOP-0001" if merchant_id == MERCHANT_ID else "SHOP-0002",
        shop_name="Synthetic Electronics",
        device_pairing_id="01JCPAIRING000000000000001",
        device_label="Counter tablet 1",
        access_expires_at=PAIRED_AT + timedelta(hours=12),
    )


PRINCIPAL = build_principal()
OTHER_PRINCIPAL = build_principal(OTHER_MERCHANT_ID)


@dataclass
class SaleServices:
    """The five sale services and the doubles behind them."""

    start_sale: StartSaleService
    list_counter_sales: ListCounterSalesService
    get_sale: GetSaleService
    issue_qr_token: IssueQrTokenService
    mark_ready_to_pay: MarkSaleReadyToPayService
    qr_token_signer: QrTokenSigner
    session_code_generator: LowestFreeSessionCodeGenerator


def wire_sale_services(kit: ServiceTestKit) -> SaleServices:
    """Builds the services on the kit's fakes with a fixed QR key and the IST calendar."""
    signer = QrTokenSigner(QR_SIGNING_KEY, kit.clock)
    issuer = CustomerQrLinkIssuer(signer, CUSTOMER_WEB_BASE_URL, QR_TOKEN_LIFETIME)
    expiry = SaleExpiryStep(kit.event_bus, CHOOSING_LIFETIME)
    session_code_generator = LowestFreeSessionCodeGenerator()
    offer_discovery = OfferDiscoveryService(
        kit.payment_gateway, kit.unit_of_work_factory, kit.clock, kit.event_bus
    )
    return SaleServices(
        start_sale=StartSaleService(
            unit_of_work_factory=kit.unit_of_work_factory,
            clock=kit.clock,
            id_generator=kit.id_generator,
            event_bus=kit.event_bus,
            session_code_generator=session_code_generator,
            qr_link_issuer=issuer,
            sale_expiry=expiry,
        ),
        list_counter_sales=ListCounterSalesService(
            kit.unit_of_work_factory, kit.clock, expiry, INDIA_TIME_ZONE
        ),
        get_sale=GetSaleService(kit.unit_of_work_factory, kit.clock, expiry),
        issue_qr_token=IssueQrTokenService(kit.unit_of_work_factory, kit.clock, issuer, expiry),
        mark_ready_to_pay=MarkSaleReadyToPayService(
            kit.unit_of_work_factory, offer_discovery, kit.clock, kit.event_bus, expiry
        ),
        qr_token_signer=signer,
        session_code_generator=session_code_generator,
    )
