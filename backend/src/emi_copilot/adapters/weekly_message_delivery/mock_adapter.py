"""MockWeeklyMessageDeliveryAdapter: "sent" means only marked sent in our database (plan Q14)."""

import logging

from emi_copilot.adapters.weekly_message_delivery.port import WeeklyMessageDeliveryPort
from emi_copilot.domain.reports.weekly_message_record import WeeklyMessageDelivery

MOCK_DELIVERY_ADAPTER_NAME = "mock"
MOCK_DELIVERY_ACTIVE_WARNING = (
    "MockWeeklyMessageDeliveryAdapter active: weekly messages are marked sent, never sent"
)

mock_delivery_logger = logging.getLogger(__name__)


# Pattern: Adapter. A labelled stand-in for a messaging channel; nothing leaves the process.
class MockWeeklyMessageDeliveryAdapter(WeeklyMessageDeliveryPort):
    """Sends nothing and stores nothing; logs that a delivery happened, without its text."""

    def __init__(self) -> None:
        """Announces in the log that weekly message delivery is mocked."""
        mock_delivery_logger.warning(
            MOCK_DELIVERY_ACTIVE_WARNING,
            extra={"weekly_message_delivery_adapter": MOCK_DELIVERY_ADAPTER_NAME},
        )

    @property
    def adapter_name(self) -> str:
        """Gives "mock"."""
        return MOCK_DELIVERY_ADAPTER_NAME

    def deliver_weekly_message(self, delivery: WeeklyMessageDelivery) -> None:
        """Logs the shop and the week only; the message text is never logged."""
        mock_delivery_logger.info(
            "weekly message delivery simulated",
            extra={
                "merchant_id": delivery.merchant_id,
                "period_start_date": delivery.period_start_date.isoformat(),
            },
        )
