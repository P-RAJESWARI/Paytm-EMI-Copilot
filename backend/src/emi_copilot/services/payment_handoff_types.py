"""The create-payment-link command, its request fingerprint, and the hand-off it returns."""

import hashlib
import json
from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidPaymentAttemptError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import (
    OfferDiscoveryQuery,
    OfferSnapshot,
    PaymentAttempt,
    PaymentAttemptStatus,
)

# The payment_attempt.idempotency_key column holds at most 255 characters.
MAXIMUM_IDEMPOTENCY_KEY_LENGTH = 255


@dataclass(frozen=True, slots=True)
class CreatePaymentLinkCommand:
    """Asks for a payment link on one offer for one item; prices are re-checked server-side.

    The offer id names the plan only. Every figure of the plan is taken from a fresh gateway
    quote, never from the caller (security-and-compliance.md section 1).
    """

    idempotency_key: str
    offer_id: str
    price: Money
    product_id: str
    brand_id: str
    category_id: str

    def __post_init__(self) -> None:
        """Rejects an empty or overlong key, and an item query that could not be sent."""
        if (
            not isinstance(self.idempotency_key, str)
            or not self.idempotency_key.strip()
            or len(self.idempotency_key) > MAXIMUM_IDEMPOTENCY_KEY_LENGTH
        ):
            raise InvalidPaymentAttemptError(
                f"The idempotency key must be 1 to {MAXIMUM_IDEMPOTENCY_KEY_LENGTH} characters."
            )
        self.to_offer_discovery_query()

    def to_offer_discovery_query(self) -> OfferDiscoveryQuery:
        """Gives the query that re-discovers the offers for this command's item and price."""
        return OfferDiscoveryQuery(
            price=self.price,
            product_id=self.product_id,
            brand_id=self.brand_id,
            category_id=self.category_id,
        )

    def calculate_request_fingerprint(self) -> str:
        """Gives the SHA-256 hex of the canonical body: sorted compact JSON, price in paise.

        The idempotency key itself is not part of the body (ADR 0005).
        """
        canonical_body = {
            "brand_id": self.brand_id,
            "category_id": self.category_id,
            "offer_id": self.offer_id,
            "price_in_paise": self.price.to_paise(),
            "product_id": self.product_id,
        }
        canonical_text = json.dumps(
            canonical_body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PaymentLinkHandoff:
    """A payment link ready to show: the order, the URL, the amount and the frozen plan.

    is_replay tells whether this is the stored result of an earlier request with the same key.
    """

    payment_attempt_id: str
    order_id: str
    payment_url: str
    amount: Money
    offer: OfferSnapshot
    status: PaymentAttemptStatus
    is_replay: bool

    @classmethod
    def from_attempt(
        cls, payment_attempt: PaymentAttempt, payment_url: str, *, is_replay: bool
    ) -> "PaymentLinkHandoff":
        """Builds the hand-off from a stored attempt whose link URL is known."""
        return cls(
            payment_attempt_id=payment_attempt.id,
            order_id=payment_attempt.order_id,
            payment_url=payment_url,
            amount=payment_attempt.amount,
            offer=payment_attempt.offer_snapshot,
            status=payment_attempt.status,
            is_replay=is_replay,
        )
