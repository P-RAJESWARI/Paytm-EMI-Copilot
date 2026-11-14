"""SettlementPort: what brands are expected to pay a shop for its no-cost EMI sales (ADR 0006)."""

from abc import ABC, abstractmethod

from emi_copilot.domain.settlements import BrandSettlementBatch


# Pattern: Port and Adapter. Services read settlements through this interface, so the labelled
# Mock (the only implementation until a real settlement source exists) can be swapped later.
class SettlementPort(ABC):
    """Brand settlement batches seen from our side, in our domain's words only."""

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Gives the short, stable name of this implementation, such as "mock"."""

    @abstractmethod
    def find_expected_brand_settlements(self, shop_code: str) -> tuple[BrandSettlementBatch, ...]:
        """Gives the batches brands are still expected to pay the shop; empty when none.

        Not filtered by any report range (plan Q13): it is what is still to come.
        """
