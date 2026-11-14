"""STUB until Phase 3C: the DESIGN_SPEC.md section 4 sample shop, item, QR codes and receipt.

Layer 2 owns the real shop, catalogue and QR tokens; these constants let the Phase 3A contract
answer with design figures computed by the real engines. Every value is synthetic.
"""

from dataclasses import dataclass
from datetime import timedelta
from types import MappingProxyType

from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import OfferDiscoveryQuery
from emi_copilot.services.plan_advice_types import CheaperModelCandidate

STUB_SHOP_NAME = "Ravi Electronics"
STUB_SHOP_ID = "RAVI-0193"
STUB_COUNTER_NAME = "Counter tablet 1"
STUB_BRAND_ID = "stub-brand-example"
STUB_CATEGORY_ID = "stub-category-phones"
STUB_ITEM_PRODUCT_NAME = "Example phone, 128 GB"
STUB_ITEM = OfferDiscoveryQuery(
    price=Money.from_rupees(22000),
    product_id="stub-product-phone-128gb",
    brand_id=STUB_BRAND_ID,
    category_id=STUB_CATEGORY_ID,
)
STUB_CHEAPER_MODEL = CheaperModelCandidate(
    product_id="stub-product-phone-64gb",
    product_name="Example phone, 64 GB",
    price=Money.from_rupees(18000),
    brand_id=STUB_BRAND_ID,
    category_id=STUB_CATEGORY_ID,
)
STUB_RECEIPT_REFERENCE = "EMI-2611-0042"
STUB_PHONE_LAST_TWO_DIGITS = "42"
STUB_ONE_TIME_CODE = "123456"
"""The fixed stub one-time code; Phase 3C sends a real one and never stores it in plain text."""

STUB_SESSION_LIFETIME = timedelta(minutes=30)
STUB_ONE_TIME_CODE_LIFETIME = timedelta(minutes=5)
STUB_ONE_TIME_CODE_RESEND_DELAY = timedelta(seconds=30)
STUB_PROFILES_ARE_SYNTHETIC = True


@dataclass(frozen=True, slots=True)
class StubQrCode:
    """STUB until Phase 3C: a sample QR token bound to one fixed customer session and its code."""

    qr_token: str
    customer_session_id: str
    session_code: str


STUB_STANDARD_QR_CODE = StubQrCode(
    qr_token="stub-qr-4821",  # noqa: S106 - a published sample QR value, not a secret
    customer_session_id="stub-customer-session-4821",
    session_code="4821",
)
"""The design's customer (inflow ₹30,000, existing EMIs ₹8,000)."""

STUB_RISKY_QR_CODE = StubQrCode(
    qr_token="stub-qr-4822",  # noqa: S106 - a published sample QR value, not a secret
    customer_session_id="stub-customer-session-4822",
    session_code="4822",
)
"""The design's second customer (inflow ₹20,000); its session id is the Mock's risky profile."""

STUB_RISKY_CUSTOMER_SESSION_ID = STUB_RISKY_QR_CODE.customer_session_id
STUB_QR_CODES_BY_TOKEN = MappingProxyType(
    {qr_code.qr_token: qr_code for qr_code in (STUB_STANDARD_QR_CODE, STUB_RISKY_QR_CODE)}
)
