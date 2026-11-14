"""The one table that says how a gateway report about a payment moves a payment attempt.

Reports arrive late, twice and out of order: a webhook can overtake a status check, and the
gateway repeats webhooks. So a report that is not in the table is "no change", never an error;
raising would only make the gateway resend a webhook that can never apply.

Rules:
- LINK_CREATED, OUTCOME_UNKNOWN and PAYMENT_PENDING follow the report to PAYMENT_PENDING, PAID
  or PAYMENT_FAILED (a PENDING report on PAYMENT_PENDING is no change).
- PAID is final: no report ever moves it, so a paid attempt is never downgraded.
- PAYMENT_FAILED moves only to PAID: a customer may pay on the same link after a failed try,
  and money received is always recorded. A late PENDING or FAILED report changes nothing.
- NOT_FOUND changes nothing anywhere.
- LINK_CREATION_IN_PROGRESS and LINK_CREATION_FAILED ignore every report: no link was handed
  out, and the in-progress attempt belongs to the create-link call until it records its outcome.
"""

from collections.abc import Mapping
from types import MappingProxyType

from emi_copilot.domain.payments.gateway_payment_status import GatewayPaymentStatus
from emi_copilot.domain.payments.payment_attempt_status import PaymentAttemptStatus

_AttemptStatus = PaymentAttemptStatus
_ReportedStatus = GatewayPaymentStatus

STATUS_AFTER_GATEWAY_REPORT: Mapping[
    tuple[PaymentAttemptStatus, GatewayPaymentStatus], PaymentAttemptStatus
] = MappingProxyType(
    {
        (_AttemptStatus.LINK_CREATED, _ReportedStatus.PENDING): _AttemptStatus.PAYMENT_PENDING,
        (_AttemptStatus.LINK_CREATED, _ReportedStatus.PAID): _AttemptStatus.PAID,
        (_AttemptStatus.LINK_CREATED, _ReportedStatus.FAILED): _AttemptStatus.PAYMENT_FAILED,
        (_AttemptStatus.OUTCOME_UNKNOWN, _ReportedStatus.PENDING): _AttemptStatus.PAYMENT_PENDING,
        (_AttemptStatus.OUTCOME_UNKNOWN, _ReportedStatus.PAID): _AttemptStatus.PAID,
        (_AttemptStatus.OUTCOME_UNKNOWN, _ReportedStatus.FAILED): _AttemptStatus.PAYMENT_FAILED,
        (_AttemptStatus.PAYMENT_PENDING, _ReportedStatus.PAID): _AttemptStatus.PAID,
        (_AttemptStatus.PAYMENT_PENDING, _ReportedStatus.FAILED): _AttemptStatus.PAYMENT_FAILED,
        (_AttemptStatus.PAYMENT_FAILED, _ReportedStatus.PAID): _AttemptStatus.PAID,
    }
)
"""Every move that changes a status; any pair not listed leaves the status as it is."""


def find_status_after_gateway_report(
    current_status: PaymentAttemptStatus, reported_status: GatewayPaymentStatus
) -> PaymentAttemptStatus:
    """Gives the attempt's status after the report; the current status means no change."""
    return STATUS_AFTER_GATEWAY_REPORT.get((current_status, reported_status), current_status)
