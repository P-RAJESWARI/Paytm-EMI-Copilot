"""MockPaytmCustomerContactAdapter: one synthetic phone number ending 42 for every sale."""

import logging

from emi_copilot.adapters.customer_contact.port import CustomerContactPort
from emi_copilot.domain.consent import CustomerPhoneNumber

MOCK_CUSTOMER_CONTACT_ADAPTER_NAME = "mock"
MOCK_CUSTOMER_CONTACT_ACTIVE_WARNING = (
    "MockPaytmCustomerContactAdapter active: every customer has one synthetic phone number"
)
SYNTHETIC_CUSTOMER_PHONE_NUMBER = CustomerPhoneNumber("9000000042")
"""Fictional and clearly synthetic: nine zeros between a 9 and 42, the design's "ending 42"."""

mock_customer_contact_logger = logging.getLogger(__name__)


# Pattern: Adapter (Mock). Stands in for the payment side's record of the customer's number. We
# know of no Paytm API that gives a merchant the number before payment without the customer
# signing in with Paytm, so the real source is [Verify with Paytm] (ADR 0022 decision 2).
class MockPaytmCustomerContactAdapter(CustomerContactPort):
    """Gives the same synthetic number for every sale and announces itself when built."""

    def __init__(self) -> None:
        """Announces in the startup log that the customer's phone number is mocked."""
        mock_customer_contact_logger.warning(
            MOCK_CUSTOMER_CONTACT_ACTIVE_WARNING,
            extra={"customer_contact_adapter": MOCK_CUSTOMER_CONTACT_ADAPTER_NAME},
        )

    @property
    def adapter_name(self) -> str:
        """Gives "mock"."""
        return MOCK_CUSTOMER_CONTACT_ADAPTER_NAME

    def find_customer_phone_number(self, sale_id: str) -> CustomerPhoneNumber | None:  # noqa: ARG002 - one number for every sale
        """Gives the synthetic number ending 42, whatever the sale."""
        return SYNTHETIC_CUSTOMER_PHONE_NUMBER
