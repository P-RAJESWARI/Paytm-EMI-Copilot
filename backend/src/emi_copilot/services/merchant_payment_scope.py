"""Which payment attempts a shop may see: only those of its own counter sales."""

from emi_copilot.domain.payments import PaymentAttempt
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork


def find_merchant_payment_attempt(
    unit_of_work: UnitOfWork, merchant_id: str, order_id: str
) -> PaymentAttempt | None:
    """Gives the attempt for the order only if it pays for one of the shop's sales, else None.

    Another shop's attempt and an attempt made for no sale both give None, so callers answer
    them exactly like an unknown order id (404).
    """
    attempt = unit_of_work.payment_attempts.find_by_order_id(order_id)
    if attempt is None or attempt.sale_id is None:
        return None
    sale = unit_of_work.sales.find_by_id_for_merchant(merchant_id, attempt.sale_id)
    return None if sale is None else attempt
