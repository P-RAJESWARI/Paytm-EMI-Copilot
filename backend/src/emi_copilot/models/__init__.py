"""SQLAlchemy ORM tables; only repositories import these, and they never leave a repository."""

from emi_copilot.models.audit_event import AuditEventModel
from emi_copilot.models.base import Base
from emi_copilot.models.consent_otp_challenge import ConsentOtpChallengeModel
from emi_copilot.models.consent_record import ConsentRecordModel
from emi_copilot.models.customer_session import CustomerSessionModel
from emi_copilot.models.device_pairing import DevicePairingModel
from emi_copilot.models.funnel_event import FunnelEventModel
from emi_copilot.models.merchant import MerchantModel
from emi_copilot.models.payment_attempt import PaymentAttemptModel
from emi_copilot.models.product import ProductModel
from emi_copilot.models.sale import SaleModel
from emi_copilot.models.weekly_message import WeeklyMessageModel

__all__ = [
    "AuditEventModel",
    "Base",
    "ConsentOtpChallengeModel",
    "ConsentRecordModel",
    "CustomerSessionModel",
    "DevicePairingModel",
    "FunnelEventModel",
    "MerchantModel",
    "PaymentAttemptModel",
    "ProductModel",
    "SaleModel",
    "WeeklyMessageModel",
]
