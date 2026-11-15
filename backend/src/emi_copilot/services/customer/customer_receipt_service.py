"""CustomerReceiptService: the C10 receipt from the consent evidence and the sale's status."""

from emi_copilot.core.clock import Clock
from emi_copilot.domain.errors import ConsentNotGivenError, InvalidSaleDataError
from emi_copilot.domain.payments import PaymentAttempt
from emi_copilot.domain.payments.payment_attempt_status import (
    STATUSES_ENDED_WITHOUT_A_PAYABLE_LINK,
)
from emi_copilot.domain.sales import Sale, SaleStatus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.customer.consent_types import (
    CoolingOffNoticeStatus,
    CustomerReceipt,
    ReceiptStatus,
)
from emi_copilot.services.customer.customer_session_access import CustomerSessionAccess
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.sale_expiry import SaleExpiryStep


def describe_receipt_status(sale: Sale, latest_attempt: PaymentAttempt | None) -> ReceiptStatus:
    """Gives where the purchase stands; a payment that did not go through is never "declined".

    A READY_TO_PAY sale whose latest payment attempt may still be paid (in progress, created,
    pending or of unknown outcome) is PAYMENT_PENDING; with no attempt, or one that ended without
    a payable link, the hand-off to the merchant is still open (READY_TO_PAY).
    """
    if sale.status is SaleStatus.PAID:
        return ReceiptStatus.PAID
    if sale.status is SaleStatus.PAYMENT_NOT_COMPLETED:
        return ReceiptStatus.PAYMENT_NOT_COMPLETED
    if sale.status is not SaleStatus.READY_TO_PAY:
        raise InvalidSaleDataError("A sale with consent evidence is always past CHOOSING.")
    if latest_attempt is None or latest_attempt.status in STATUSES_ENDED_WITHOUT_A_PAYABLE_LINK:
        return ReceiptStatus.READY_TO_PAY
    return ReceiptStatus.PAYMENT_PENDING


class CustomerReceiptService:
    """Gives the customer's own receipt: reference, plan as agreed, phone ending, language.

    There is no payment URL, because the merchant takes the payment on Paytm (rule 9), and the
    cooling-off wording stays a placeholder until the lender confirms the period.
    """

    def __init__(
        self, unit_of_work_factory: UnitOfWorkFactory, clock: Clock, sale_expiry: SaleExpiryStep
    ) -> None:
        """Keeps the unit-of-work factory, the clock and the session check."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._session_access = CustomerSessionAccess(sale_expiry)

    def get_receipt(self, credentials: CustomerSessionCredentials) -> CustomerReceipt:
        """Gives C10 for the session's sale; before consent it raises ConsentNotGivenError."""
        with self._unit_of_work_factory() as unit_of_work:
            opened = self._session_access.open_sale(unit_of_work, credentials, self._clock.now())
            consent_record = unit_of_work.consent_records.find_for_sale(opened.sale.id)
            if consent_record is None:
                raise ConsentNotGivenError("There is no receipt until the plan is agreed.")
            latest_attempt = unit_of_work.payment_attempts.find_latest_for_sale(opened.sale.id)
        return CustomerReceipt(
            status=describe_receipt_status(opened.sale, latest_attempt),
            consent_record=consent_record,
            cooling_off_notice_status=CoolingOffNoticeStatus(
                consent_record.evidence.cooling_off_wording_version
            ),
        )
