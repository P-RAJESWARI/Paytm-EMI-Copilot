"""WeeklyMessageDeliveryPort: sends a shop its weekly message (plan Q14)."""

from abc import ABC, abstractmethod

from emi_copilot.domain.reports.weekly_message_record import WeeklyMessageDelivery


# Pattern: Port and Adapter. Services send through this interface; the labelled Mock sends
# nothing, and a real channel (SMS, WhatsApp) would be one more adapter behind it.
class WeeklyMessageDeliveryPort(ABC):
    """Delivers one week's message to one shop."""

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Gives the short, stable name of this implementation, such as "mock"."""

    @abstractmethod
    def deliver_weekly_message(self, delivery: WeeklyMessageDelivery) -> None:
        """Sends the message; called at most once per shop and week, after it is recorded."""
