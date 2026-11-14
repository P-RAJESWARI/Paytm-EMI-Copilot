"""SaleStateMachine: the two tables that say how commands and payment reports move a sale."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from emi_copilot.domain.errors import IllegalSaleTransitionError
from emi_copilot.domain.sales.sale_status import SaleStatus


class SaleCommand(StrEnum):
    """Something a person or a timer asks a sale to do; refused unless the table allows it."""

    AGREE_TO_PLAN = "AGREE_TO_PLAN"
    """The customer agreed to one plan (Layer 3 consent, or the 2.3 Mock customer simulator)."""

    ISSUE_QR_CODE = "ISSUE_QR_CODE"
    """The merchant shows a fresh QR code, which voids the previous one."""

    EXPIRE = "EXPIRE"
    """The choosing time ran out before the customer agreed to a plan."""

    RETRY_PAYMENT = "RETRY_PAYMENT"
    """The merchant tries the payment again after it did not go through."""


class SalePaymentOutcome(StrEnum):
    """What the gateway reported about a sale's payment, confirmed server-side."""

    PAID = "PAID"
    NOT_COMPLETED = "NOT_COMPLETED"


class PaymentOutcomeEffect(StrEnum):
    """What applying one payment report did; none of them is an error."""

    STATUS_CHANGED = "STATUS_CHANGED"
    """The sale moved to a new status."""

    NO_CHANGE = "NO_CHANGE"
    """A repeated or late report about a sale that already moved on, such as a paid one."""

    IGNORED_NOT_AWAITING_PAYMENT = "IGNORED_NOT_AWAITING_PAYMENT"
    """The sale is CHOOSING or EXPIRED, so no payment was expected; the report is audited."""


STATUS_AFTER_COMMAND: Mapping[tuple[SaleStatus, SaleCommand], SaleStatus] = MappingProxyType(
    {
        (SaleStatus.CHOOSING, SaleCommand.AGREE_TO_PLAN): SaleStatus.READY_TO_PAY,
        (SaleStatus.CHOOSING, SaleCommand.ISSUE_QR_CODE): SaleStatus.CHOOSING,
        (SaleStatus.CHOOSING, SaleCommand.EXPIRE): SaleStatus.EXPIRED,
        (SaleStatus.PAYMENT_NOT_COMPLETED, SaleCommand.RETRY_PAYMENT): SaleStatus.READY_TO_PAY,
    }
)
"""Every legal command; any (status, command) pair not listed is refused."""

STATUS_AFTER_PAYMENT_OUTCOME: Mapping[tuple[SaleStatus, SalePaymentOutcome], SaleStatus] = (
    MappingProxyType(
        {
            (SaleStatus.READY_TO_PAY, SalePaymentOutcome.PAID): SaleStatus.PAID,
            (
                SaleStatus.READY_TO_PAY,
                SalePaymentOutcome.NOT_COMPLETED,
            ): SaleStatus.PAYMENT_NOT_COMPLETED,
            (SaleStatus.PAYMENT_NOT_COMPLETED, SalePaymentOutcome.PAID): SaleStatus.PAID,
        }
    )
)
"""Every payment report that moves a sale; any other pair leaves the status as it is."""

STATUSES_NOT_AWAITING_PAYMENT = frozenset({SaleStatus.CHOOSING, SaleStatus.EXPIRED})
"""No plan was agreed in these statuses, so a payment report about them is out of place."""


@dataclass(frozen=True, slots=True)
class PaymentOutcomeDecision:
    """The status after a payment report and what the report did."""

    status: SaleStatus
    effect: PaymentOutcomeEffect


# Pattern: State. Legal sale moves live in two tables instead of status checks scattered across
# services, so every (status, command) pair is explicit and tested.
class SaleStateMachine:
    """Decides sale moves: strict for commands, tolerant for gateway payment reports.

    Commands (STATUS_AFTER_COMMAND), any other pair raises IllegalSaleTransitionError (409):

    | From                  | Command       | To           |
    |-----------------------|---------------|--------------|
    | CHOOSING              | AGREE_TO_PLAN | READY_TO_PAY |
    | CHOOSING              | ISSUE_QR_CODE | CHOOSING     |
    | CHOOSING              | EXPIRE        | EXPIRED      |
    | PAYMENT_NOT_COMPLETED | RETRY_PAYMENT | READY_TO_PAY |

    Payment reports (STATUS_AFTER_PAYMENT_OUTCOME) never raise, because reports arrive late,
    twice and out of order, as for payment attempts:

    | From                  | PAID report         | NOT_COMPLETED report  |
    |-----------------------|---------------------|-----------------------|
    | READY_TO_PAY          | PAID                | PAYMENT_NOT_COMPLETED |
    | PAYMENT_NOT_COMPLETED | PAID (late success) | no change (repeat)    |
    | PAID                  | no change (final)   | no change (final)     |
    | CHOOSING, EXPIRED     | ignored and audited | ignored and audited   |
    """

    def status_after_command(self, current_status: SaleStatus, command: SaleCommand) -> SaleStatus:
        """Gives the status the command leads to, or raises when the table does not allow it."""
        next_status = STATUS_AFTER_COMMAND.get((current_status, command))
        if next_status is None:
            raise IllegalSaleTransitionError(
                f"A sale that is {current_status.value} cannot take the command {command.value}."
            )
        return next_status

    def decide_payment_outcome(
        self, current_status: SaleStatus, outcome: SalePaymentOutcome
    ) -> PaymentOutcomeDecision:
        """Gives the status after a payment report and its effect; it never raises."""
        if current_status in STATUSES_NOT_AWAITING_PAYMENT:
            return PaymentOutcomeDecision(
                current_status, PaymentOutcomeEffect.IGNORED_NOT_AWAITING_PAYMENT
            )
        next_status = STATUS_AFTER_PAYMENT_OUTCOME.get((current_status, outcome))
        if next_status is None:
            return PaymentOutcomeDecision(current_status, PaymentOutcomeEffect.NO_CHANGE)
        return PaymentOutcomeDecision(next_status, PaymentOutcomeEffect.STATUS_CHANGED)
