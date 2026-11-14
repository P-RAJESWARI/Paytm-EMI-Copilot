"""MockSettlementAdapter: the DESIGN_SPEC money-due batches for the demo shop (rule 10)."""

import logging
from datetime import date
from types import MappingProxyType

from emi_copilot.adapters.settlement.port import SettlementPort
from emi_copilot.domain.money import Money
from emi_copilot.domain.settlements import BrandSettlementBatch, BrandSettlementStatus

MOCK_SETTLEMENT_ADAPTER_NAME = "mock"
MOCK_SETTLEMENT_ACTIVE_WARNING = (
    "MockSettlementAdapter active: brand settlement batches are synthetic demo data"
)
DEMO_SHOP_CODE = "RAVI-0193"

mock_settlement_logger = logging.getLogger(__name__)

_DEMO_BATCHES_BY_SHOP_CODE = MappingProxyType(
    {
        DEMO_SHOP_CODE: (
            BrandSettlementBatch(
                1, 18, Money.from_rupees("72000"), date(2027, 1, 13),
                BrandSettlementStatus.CLAIM_FILED,
            ),
            BrandSettlementBatch(
                2, 16, Money.from_rupees("64000"), date(2027, 1, 28),
                BrandSettlementStatus.WAITING_FOR_BRAND,
            ),
            BrandSettlementBatch(
                3, 10, Money.from_rupees("48000"), date(2027, 2, 12),
                BrandSettlementStatus.NOT_YET_DUE,
            ),
        )
    }
)  # fmt: skip
"""DESIGN_SPEC section 4: ₹1,84,000 in three batches, for the demo shop only."""


# Pattern: Adapter. A labelled stand-in for brand settlement data that does not exist yet.
class MockSettlementAdapter(SettlementPort):
    """Gives the three design batches for RAVI-0193 and nothing for any other shop."""

    def __init__(self) -> None:
        """Announces in the log that settlement data is mocked."""
        mock_settlement_logger.warning(
            MOCK_SETTLEMENT_ACTIVE_WARNING,
            extra={"settlement_adapter": MOCK_SETTLEMENT_ADAPTER_NAME},
        )

    @property
    def adapter_name(self) -> str:
        """Gives "mock"."""
        return MOCK_SETTLEMENT_ADAPTER_NAME

    def find_expected_brand_settlements(self, shop_code: str) -> tuple[BrandSettlementBatch, ...]:
        """Gives the demo batches for the demo shop; any other shop has none."""
        return _DEMO_BATCHES_BY_SHOP_CODE.get(shop_code, ())
