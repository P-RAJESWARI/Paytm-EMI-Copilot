"""LatestSaleAttemptCheck: settles a sale's latest payment attempt before a new key links it."""

from datetime import timedelta

from emi_copilot.core.clock import Clock
from emi_copilot.domain.payments import GatewayPaymentStatus, PaymentAttempt, PaymentAttemptStatus
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.create_link_outcome import record_stale_link_creation_as_unknown
from emi_copilot.services.payment_status_service import PaymentStatusService


class LatestSaleAttemptCheck:
    """Keeps a sale's payment from being blocked for ever by an attempt that has no link.

    A new key is refused while the sale's latest attempt may still be paid. Two such attempts
    could otherwise never end, so before a new key is tried this check settles them:

    - LINK_CREATION_IN_PROGRESS, left by a crash between the two create transactions: once its
      creation is at least link_creation_stale_after in the past, it is stored as OUTCOME_UNKNOWN
      under its row lock (audited LINK_CREATION_STALE), whatever key asks.
    - OUTCOME_UNKNOWN, left by a create timeout (or by the step above): once its creation is at
      least link_creation_stale_after in the past, the gateway is asked for its status (an
      idempotent read). NOT_FOUND then proves no link exists, so the sale may take a new one.

    Age is measured from the attempt's created_at, the moment its only create call was sent: the
    limit is twice the longest that call can wait, so past it the call has surely ended and a
    NOT_FOUND cannot race a link still being made. The attempt row is never changed by the
    NOT_FOUND (it stays as evidence, and a late gateway report still applies to it); PENDING, PAID
    and FAILED answers are applied to it as any status check applies them. The old create call
    is never re-sent.
    """

    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        event_bus: DomainEventBus,
        payment_status_service: PaymentStatusService,
        link_creation_stale_after: timedelta,
    ) -> None:
        """Keeps the collaborators and how long after its creation an attempt counts as stale."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._event_bus = event_bus
        self._payment_status_service = payment_status_service
        self._link_creation_stale_after = link_creation_stale_after

    def find_attempt_proven_without_link(self, sale_id: str) -> str | None:
        """Settles the sale's latest attempt; gives its id when the gateway proved it has no link.

        None means nothing was proven: the sale's usual new-link rule then decides.
        """
        latest_attempt = self._record_stale_link_creation(sale_id)
        if (
            latest_attempt is None
            or latest_attempt.status is not PaymentAttemptStatus.OUTCOME_UNKNOWN
            or not self._is_past_stale_limit(latest_attempt)
        ):
            return None
        status_view = self._payment_status_service.get_payment_status(latest_attempt.order_id)
        if status_view.reported_status is GatewayPaymentStatus.NOT_FOUND:
            return latest_attempt.id
        return None

    def _record_stale_link_creation(self, sale_id: str) -> PaymentAttempt | None:
        """Gives the sale's latest attempt, stored first as OUTCOME_UNKNOWN if stale in progress."""
        with self._unit_of_work_factory() as unit_of_work:
            latest_attempt = unit_of_work.payment_attempts.find_latest_for_sale(sale_id)
            if (
                latest_attempt is None
                or latest_attempt.status is not PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS
                or not self._is_past_stale_limit(latest_attempt)
            ):
                return latest_attempt
            return record_stale_link_creation_as_unknown(
                unit_of_work, latest_attempt, self._event_bus, self._clock.now()
            )

    def _is_past_stale_limit(self, attempt: PaymentAttempt) -> bool:
        """Tells whether the attempt's only create call was sent at least the stale limit ago."""
        return self._clock.now() - attempt.created_at >= self._link_creation_stale_after
