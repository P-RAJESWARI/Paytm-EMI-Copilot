"""What the sale services return: a sale with its product name, and the customer QR link."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime

from emi_copilot.domain.errors import InvalidSaleDataError, ProductNotFoundError
from emi_copilot.domain.sales import Sale
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork

# The sale.idempotency_key column holds at most 255 characters.
MAXIMUM_SALE_IDEMPOTENCY_KEY_LENGTH = 255


@dataclass(frozen=True, slots=True)
class CounterSale:
    """A sale as the counter shows it: the sale itself and the name of the product sold."""

    sale: Sale
    product_name: str


@dataclass(frozen=True, slots=True)
class CustomerQrLink:
    """The URL the QR code encodes (token in the #t= fragment) and when the token stops working.

    The URL is shown once and never stored or logged, so it is kept out of repr.
    """

    customer_url: str = field(repr=False)
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class StartedSale:
    """A started sale with its first QR link; a replayed start has no link (tokens aren't kept)."""

    counter_sale: CounterSale
    qr_link: CustomerQrLink | None
    is_replay: bool


@dataclass(frozen=True, slots=True)
class StartSaleCommand:
    """Start a sale of one catalogue product at its list price, maybe under an Idempotency-Key."""

    product_id: str
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        """Rejects a blank product id and a blank or overlong key."""
        if not self.product_id.strip():
            raise InvalidSaleDataError("A sale needs a product id.")
        if self.idempotency_key is not None and not (
            self.idempotency_key.strip()
            and len(self.idempotency_key) <= MAXIMUM_SALE_IDEMPOTENCY_KEY_LENGTH
        ):
            raise InvalidSaleDataError(
                f"An idempotency key has 1 to {MAXIMUM_SALE_IDEMPOTENCY_KEY_LENGTH} characters."
            )

    def calculate_request_fingerprint(self) -> str:
        """Gives the SHA-256 hex of the canonical body, so a key reused on a new body is caught."""
        canonical_text = json.dumps(
            {"product_id": self.product_id}, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()


def build_counter_sale(unit_of_work: UnitOfWork, sale: Sale) -> CounterSale:
    """Pairs a sale with its product's name, read from the same merchant's catalogue."""
    product = unit_of_work.products.find_by_id_for_merchant(sale.merchant_id, sale.product_id)
    if product is None:
        raise ProductNotFoundError("The product of a stored sale is not in the shop's catalogue.")
    return CounterSale(sale=sale, product_name=product.name)
