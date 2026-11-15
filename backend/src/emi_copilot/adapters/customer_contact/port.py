"""CustomerContactPort: the customer's phone number as the payment side knows it (ADR 0022)."""

from abc import ABC, abstractmethod

from emi_copilot.domain.consent import CustomerPhoneNumber


# Pattern: Port and Adapter. The consent service asks this interface for the number to send the
# one-time code to, so the labelled Mock and a future Paytm source are interchangeable.
class CustomerContactPort(ABC):
    """Gives the phone number behind a sale, in our domain's terms only.

    The number is used only in memory, to send the code; callers store its last two digits and
    a keyed hash, never the number (security-and-compliance.md section 2).
    """

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Gives the short, stable name of this implementation, such as "mock"."""

    @abstractmethod
    def find_customer_phone_number(self, sale_id: str) -> CustomerPhoneNumber | None:
        """Gives the customer's phone number for the sale, or None when the source has none."""
