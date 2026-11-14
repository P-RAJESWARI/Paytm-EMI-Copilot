"""PaymentHandoffService: creates a payment link at most once per Idempotency-Key (ADR 0005)."""

from dataclasses import replace

from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.domain.errors import (
    DomainError,
    IdempotencyKeyReusedError,
    InvalidPaymentGatewayValueError,
    OfferNotFoundError,
    PaymentAttemptAlreadyExistsError,
    PaymentGatewayRequestRejectedError,
    PaymentGatewayTimeoutError,
    PaymentGatewayUnavailableError,
    PaymentLinkCreationFailedError,
    PaymentLinkCreationInProgressError,
    PaymentLinkOutcomeUnknownError,
)
from emi_copilot.domain.events import (
    PaymentLinkCreated,
    PaymentLinkCreationFailed,
    PaymentLinkOutcomeUnknown,
)
from emi_copilot.domain.payments import (
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentLink,
    PaymentLinkRequest,
    find_payment_link_failure_code,
    price_emi_offer,
)
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.create_link_outcome import (
    describe_create_link_attempt,
    save_create_link_outcome,
)
from emi_copilot.services.payment_handoff_types import (
    CreatePaymentLinkCommand,
    PaymentLinkHandoff,
)

# Cause code audited when create-link fails with an exception that carries no domain code.
UNEXPECTED_FAILURE_CAUSE_CODE = "UNEXPECTED_ERROR"


def replay_stored_outcome(
    stored_attempt: PaymentAttempt, request_fingerprint: str
) -> PaymentLinkHandoff:
    """Gives the stored link for a repeated key, or raises the typed error of its outcome.

    A different body is IDEMPOTENCY_KEY_REUSED. An attempt without a stored link URL raises
    instead of re-sending: in progress, failed (with its code) or outcome unknown, which also
    covers an attempt a later status report moved on from OUTCOME_UNKNOWN or from in progress.
    """
    if stored_attempt.request_fingerprint != request_fingerprint:
        raise IdempotencyKeyReusedError("The Idempotency-Key was used with a different body.")
    if stored_attempt.status is PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS:
        raise PaymentLinkCreationInProgressError("The first request with this key is running.")
    # The failure code is set exactly when the attempt is LINK_CREATION_FAILED.
    if stored_attempt.failure_code is not None:
        raise PaymentLinkCreationFailedError(
            stored_attempt.failure_code, "This key's payment link was not created."
        )
    payment_url = stored_attempt.payment_link_url
    if payment_url is None:
        raise PaymentLinkOutcomeUnknownError(
            "This key's payment link call has an unknown outcome; start again with a new key."
        )
    return PaymentLinkHandoff.from_attempt(stored_attempt, payment_url, is_replay=True)


class PaymentHandoffService:
    """Hands the chosen plan to the gateway as a payment link, exactly once per key.

    Two transactions surround one gateway call. The first stores the attempt as
    LINK_CREATION_IN_PROGRESS and commits before the call, so a concurrent request with the same
    key hits the unique constraint. The call runs outside any transaction and is never retried.
    The second transaction records the outcome and publishes its event, so the audit row
    commits with it. It locks the row first: a gateway report that arrived during the call is
    newer evidence (it may be PAID), so the call's outcome never overwrites it. If the second
    transaction itself fails, the attempt stays in progress until a gateway report moves it.
    """

    def __init__(
        self,
        payment_gateway: PaymentGatewayPort,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        id_generator: IdGenerator,
        event_bus: DomainEventBus,
    ) -> None:
        """Keeps the gateway port, unit-of-work factory, clock, id generator and event bus."""
        self._payment_gateway = payment_gateway
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._id_generator = id_generator
        self._event_bus = event_bus

    def create_payment_link(self, command: CreatePaymentLinkCommand) -> PaymentLinkHandoff:
        """Replays a known key's outcome, or creates the link once and records what happened."""
        request_fingerprint = command.calculate_request_fingerprint()
        stored_attempt = self._find_attempt_by_key(command.idempotency_key)
        if stored_attempt is not None:
            return replay_stored_outcome(stored_attempt, request_fingerprint)
        link_request = self._build_payment_link_request(command)
        new_attempt = self._build_attempt(command, request_fingerprint, link_request)
        concurrent_attempt = self._insert_attempt(new_attempt)
        if concurrent_attempt is not None:
            return replay_stored_outcome(concurrent_attempt, request_fingerprint)
        return self._call_gateway_and_record_outcome(new_attempt, link_request)

    def _find_attempt_by_key(self, idempotency_key: str) -> PaymentAttempt | None:
        """Reads the attempt stored under the key, in a short read-only transaction."""
        with self._unit_of_work_factory() as unit_of_work:
            return unit_of_work.payment_attempts.find_by_idempotency_key(idempotency_key)

    def _build_payment_link_request(self, command: CreatePaymentLinkCommand) -> PaymentLinkRequest:
        """Re-discovers the offers server-side, picks the chosen one and freezes its plan."""
        offers = self._payment_gateway.discover_offers(command.to_offer_discovery_query())
        chosen_offer = next((offer for offer in offers if offer.offer_id == command.offer_id), None)
        if chosen_offer is None:
            raise OfferNotFoundError("The chosen offer is not quoted for this item and price.")
        return PaymentLinkRequest(
            order_id=self._id_generator.new_id(),
            amount=command.price,
            offer=price_emi_offer(chosen_offer, command.price).to_offer_snapshot(),
            product_id=command.product_id,
            brand_id=command.brand_id,
            category_id=command.category_id,
            customer_reference=self._id_generator.new_id(),
        )

    def _build_attempt(
        self,
        command: CreatePaymentLinkCommand,
        request_fingerprint: str,
        link_request: PaymentLinkRequest,
    ) -> PaymentAttempt:
        """Builds the new attempt, in progress, for the order the link request names."""
        created_at = self._clock.now()
        return PaymentAttempt(
            id=self._id_generator.new_id(),
            order_id=link_request.order_id,
            idempotency_key=command.idempotency_key,
            request_fingerprint=request_fingerprint,
            amount=link_request.amount,
            status=PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS,
            offer_snapshot=link_request.offer,
            gateway_mode=self._payment_gateway.adapter_name,
            gateway_link_id=None,
            payment_link_url=None,
            gateway_transaction_id=None,
            created_at=created_at,
            updated_at=created_at,
        )

    def _insert_attempt(self, new_attempt: PaymentAttempt) -> PaymentAttempt | None:
        """Commits the in-progress attempt; gives the stored one if a concurrent request won."""
        try:
            with self._unit_of_work_factory() as unit_of_work:
                unit_of_work.payment_attempts.add(new_attempt)
        except PaymentAttemptAlreadyExistsError:
            concurrent_attempt = self._find_attempt_by_key(new_attempt.idempotency_key)
            if concurrent_attempt is None:
                raise
            return concurrent_attempt
        return None

    def _call_gateway_and_record_outcome(
        self, attempt: PaymentAttempt, link_request: PaymentLinkRequest
    ) -> PaymentLinkHandoff:
        """Calls create-link exactly once, records the outcome, then re-raises any failure."""
        try:
            payment_link = self._payment_gateway.create_payment_link(link_request)
        except (PaymentGatewayTimeoutError, InvalidPaymentGatewayValueError) as unknown_error:
            self._record_outcome_unknown(attempt, unknown_error.code)
            raise
        except (PaymentGatewayUnavailableError, PaymentGatewayRequestRejectedError) as failure:
            self._record_creation_failed(attempt, failure)
            raise
        except Exception as unexpected_error:
            # Any other failure (a bug or an untranslated library error) may have come after the
            # request reached the gateway, so the outcome is unknown (ADR 0005). Left in progress,
            # the key would answer 409 forever. It is recorded, then re-raised, never swallowed.
            self._record_unexpected_outcome_unknown(attempt, unexpected_error)
            raise
        return self._record_link_created(attempt, payment_link)

    def _record_unexpected_outcome_unknown(
        self, attempt: PaymentAttempt, unexpected_error: Exception
    ) -> None:
        """Best effort: stores OUTCOME_UNKNOWN for an unexpected create-link failure.

        If recording fails too, the original error is raised with the recording failure as its
        cause, so neither is lost; the attempt then stays in progress until a gateway report.
        """
        cause_error_code = (
            unexpected_error.code
            if isinstance(unexpected_error, DomainError)
            else UNEXPECTED_FAILURE_CAUSE_CODE
        )
        try:
            self._record_outcome_unknown(attempt, cause_error_code)
        except Exception as recording_error:
            raise unexpected_error from recording_error

    def _record_link_created(
        self, attempt: PaymentAttempt, payment_link: PaymentLink
    ) -> PaymentLinkHandoff:
        """Stores LINK_CREATED with the link and publishes PaymentLinkCreated in one transaction."""
        with self._unit_of_work_factory() as unit_of_work:
            stored_attempt = save_create_link_outcome(
                unit_of_work,
                replace(
                    attempt,
                    status=PaymentAttemptStatus.LINK_CREATED,
                    gateway_link_id=payment_link.gateway_link_id,
                    payment_link_url=payment_link.payment_url,
                ),
            )
            self._event_bus.publish(
                PaymentLinkCreated(
                    occurred_at=self._clock.now(), **describe_create_link_attempt(attempt)
                ),
                unit_of_work,
            )
        return PaymentLinkHandoff.from_attempt(
            stored_attempt, payment_link.payment_url, is_replay=False
        )

    def _record_outcome_unknown(self, attempt: PaymentAttempt, cause_error_code: str) -> None:
        """Stores OUTCOME_UNKNOWN and publishes PaymentLinkOutcomeUnknown in one transaction."""
        with self._unit_of_work_factory() as unit_of_work:
            save_create_link_outcome(
                unit_of_work, replace(attempt, status=PaymentAttemptStatus.OUTCOME_UNKNOWN)
            )
            self._event_bus.publish(
                PaymentLinkOutcomeUnknown(
                    occurred_at=self._clock.now(),
                    cause_error_code=cause_error_code,
                    **describe_create_link_attempt(attempt),
                ),
                unit_of_work,
            )

    def _record_creation_failed(
        self,
        attempt: PaymentAttempt,
        failure: PaymentGatewayUnavailableError | PaymentGatewayRequestRejectedError,
    ) -> None:
        """Stores LINK_CREATION_FAILED with its code and publishes the event in one transaction."""
        failure_code = find_payment_link_failure_code(failure)
        with self._unit_of_work_factory() as unit_of_work:
            save_create_link_outcome(
                unit_of_work,
                replace(
                    attempt,
                    status=PaymentAttemptStatus.LINK_CREATION_FAILED,
                    failure_code=failure_code,
                ),
            )
            self._event_bus.publish(
                PaymentLinkCreationFailed(
                    occurred_at=self._clock.now(),
                    failure_code=failure_code,
                    **describe_create_link_attempt(attempt),
                ),
                unit_of_work,
            )
