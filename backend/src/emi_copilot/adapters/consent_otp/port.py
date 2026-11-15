"""ConsentOtpSenderPort: sends the customer the one-time code that confirms consent (C9)."""

from abc import ABC, abstractmethod

from emi_copilot.domain.consent import CustomerPhoneNumber


# Pattern: Port and Adapter. The consent service sends codes through this interface, so the
# labelled Mock (sends nothing) and a real SMS channel are interchangeable.
class ConsentOtpSenderPort(ABC):
    """Delivers one code to one phone number; neither is ever logged or stored."""

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Gives the short, stable name of this implementation, such as "mock"."""

    @abstractmethod
    def send(self, phone_number: CustomerPhoneNumber, code: str) -> None:
        """Sends the code to the number; called once per issued challenge, after it is stored."""
