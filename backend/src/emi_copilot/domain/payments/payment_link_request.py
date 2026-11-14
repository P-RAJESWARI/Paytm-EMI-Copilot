"""PaymentLinkRequest: everything the gateway needs to make a payment link for one chosen plan."""

import re
from dataclasses import dataclass

from emi_copilot.domain.errors import InvalidPaymentGatewayValueError
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_positive_whole_paise_money,
)
from emi_copilot.domain.payments.offer_snapshot import OfferSnapshot

# Phone numbers have at least ten digits; separators people type are ignored when counting.
_PHONE_NUMBER_SEPARATORS = re.compile(r"[\s()+-]")
_MINIMUM_PHONE_NUMBER_DIGITS = 10


def _require_non_personal_customer_reference(customer_reference: str) -> None:
    """Raises when a customer reference looks like an email address or a phone number."""
    digits_only = _PHONE_NUMBER_SEPARATORS.sub("", customer_reference)
    looks_like_phone_number = (
        digits_only.isdigit() and len(digits_only) >= _MINIMUM_PHONE_NUMBER_DIGITS
    )
    if "@" in customer_reference or looks_like_phone_number:
        raise InvalidPaymentGatewayValueError(
            "The customer reference must be an opaque id, never an email or phone number."
        )


# Pattern: Value Object. The amount, the plan and the item are checked together before any call.
@dataclass(frozen=True, slots=True)
class PaymentLinkRequest:
    """Asks the gateway for a link that lets the customer pay the amount on the chosen plan.

    The amount is the item price the plan was built on, so it must equal the snapshot's total
    payable minus its extra in total. The customer reference is an opaque id we generate (such
    as a ULID). It must never be a phone number, name or email address: it leaves our system.
    The checks for "@" and long digit strings are a guard against mistakes, not a proof.
    """

    order_id: str
    amount: Money
    offer: OfferSnapshot
    product_id: str
    brand_id: str
    category_id: str
    customer_reference: str

    def __post_init__(self) -> None:
        """Rejects blank ids, an amount that is not the plan's price and a personal reference."""
        for identifier, description in (
            (self.order_id, "order id"),
            (self.product_id, "product id"),
            (self.brand_id, "brand id"),
            (self.category_id, "category id"),
            (self.customer_reference, "customer reference"),
        ):
            require_non_empty_text(identifier, description, InvalidPaymentGatewayValueError)
        require_positive_whole_paise_money(self.amount, "amount", InvalidPaymentGatewayValueError)
        if not isinstance(self.offer, OfferSnapshot):
            raise InvalidPaymentGatewayValueError("The offer must be an OfferSnapshot.")
        if self.amount != self.offer.total_payable - self.offer.extra_in_total:
            raise InvalidPaymentGatewayValueError(
                "The amount must equal the price the chosen plan was built on."
            )
        _require_non_personal_customer_reference(self.customer_reference)
