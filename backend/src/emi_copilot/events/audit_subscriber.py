"""AuditSubscriber: writes one append-only audit row for every payment and sale domain event."""

import dataclasses
from collections.abc import Callable, Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.core.request_context import get_current_correlation_id
from emi_copilot.domain.events import (
    DomainEvent,
    OfferQuoteMismatch,
    PaymentLinkCreated,
    PaymentLinkCreationFailed,
    PaymentLinkOutcomeUnknown,
    PaymentStatusChanged,
    SalePaymentOutcomeIgnored,
    SaleStarted,
    SaleStatusChanged,
    WebhookProcessed,
    WebhookRejected,
)
from emi_copilot.domain.payments import AuditDetailValue, AuditEvent, AuditEventType
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWork

PAYMENT_ATTEMPT_SUBJECT_TYPE = "payment_attempt"
WEBHOOK_DELIVERY_SUBJECT_TYPE = "webhook_delivery"
PAYMENT_ORDER_SUBJECT_TYPE = "payment_order"
EMI_OFFER_SUBJECT_TYPE = "emi_offer"
SALE_SUBJECT_TYPE = "sale"
_OCCURRED_AT_FIELD = "occurred_at"


@dataclasses.dataclass(frozen=True, slots=True)
class AuditMapping:
    """How one event type becomes an audit row: its type, its subject and the subject id field."""

    audit_event_type: AuditEventType
    subject_type: str
    subject_id_field: str


AUDIT_MAPPINGS_BY_EVENT_TYPE: Mapping[type[DomainEvent], AuditMapping] = MappingProxyType(
    {
        PaymentLinkCreated: AuditMapping(
            AuditEventType.PAYMENT_LINK_CREATED, PAYMENT_ATTEMPT_SUBJECT_TYPE, "payment_attempt_id"
        ),
        PaymentLinkCreationFailed: AuditMapping(
            AuditEventType.PAYMENT_LINK_CREATION_FAILED,
            PAYMENT_ATTEMPT_SUBJECT_TYPE,
            "payment_attempt_id",
        ),
        PaymentLinkOutcomeUnknown: AuditMapping(
            AuditEventType.PAYMENT_LINK_OUTCOME_UNKNOWN,
            PAYMENT_ATTEMPT_SUBJECT_TYPE,
            "payment_attempt_id",
        ),
        PaymentStatusChanged: AuditMapping(
            AuditEventType.PAYMENT_STATUS_CHANGED,
            PAYMENT_ATTEMPT_SUBJECT_TYPE,
            "payment_attempt_id",
        ),
        WebhookRejected: AuditMapping(
            AuditEventType.WEBHOOK_REJECTED, WEBHOOK_DELIVERY_SUBJECT_TYPE, "webhook_delivery_id"
        ),
        WebhookProcessed: AuditMapping(
            AuditEventType.WEBHOOK_PROCESSED, PAYMENT_ORDER_SUBJECT_TYPE, "order_id"
        ),
        OfferQuoteMismatch: AuditMapping(
            AuditEventType.OFFER_QUOTE_MISMATCH, EMI_OFFER_SUBJECT_TYPE, "offer_id"
        ),
        SaleStarted: AuditMapping(AuditEventType.SALE_STARTED, SALE_SUBJECT_TYPE, "sale_id"),
        SaleStatusChanged: AuditMapping(
            AuditEventType.SALE_STATUS_CHANGED, SALE_SUBJECT_TYPE, "sale_id"
        ),
        SalePaymentOutcomeIgnored: AuditMapping(
            AuditEventType.SALE_PAYMENT_OUTCOME_IGNORED, SALE_SUBJECT_TYPE, "sale_id"
        ),
    }
)


def _to_detail_value(value: object) -> AuditDetailValue:
    """Stores an enum by its value; ids, codes, paise and None pass through unchanged.

    AuditEvent itself rejects any value that is not a JSON scalar, so nothing else can slip in.
    """
    if isinstance(value, StrEnum):
        return value.value
    return cast("AuditDetailValue", value)


def build_audit_details(event: DomainEvent, subject_id_field: str) -> dict[str, AuditDetailValue]:
    """Copies every event field except the moment and the subject id into audit details."""
    return {
        event_field.name: _to_detail_value(getattr(event, event_field.name))
        for event_field in dataclasses.fields(event)
        if event_field.name not in {_OCCURRED_AT_FIELD, subject_id_field}
    }


class AuditSubscriber:
    """Turns each payment and sale domain event into an AuditEvent in the publisher's unit of work.

    The row commits with the business write or not at all (security-and-compliance.md section
    9). The correlation id is the current request's, when there is one.
    """

    def __init__(
        self,
        id_generator: IdGenerator,
        correlation_id_provider: Callable[[], str | None] = get_current_correlation_id,
    ) -> None:
        """Keeps the generator for audit row ids and the source of the request correlation id."""
        self._id_generator = id_generator
        self._correlation_id_provider = correlation_id_provider

    def subscribe_to(self, event_bus: DomainEventBus) -> None:
        """Subscribes this subscriber to every event type that has an audit mapping."""
        for event_type in AUDIT_MAPPINGS_BY_EVENT_TYPE:
            event_bus.subscribe(event_type, self.record_event)

    def record_event(self, event: DomainEvent, unit_of_work: UnitOfWork) -> None:
        """Appends the audit row for one event; an event type without a mapping raises KeyError."""
        audit_mapping = AUDIT_MAPPINGS_BY_EVENT_TYPE[type(event)]
        unit_of_work.audit_events.append(
            AuditEvent(
                id=self._id_generator.new_id(),
                event_type=audit_mapping.audit_event_type,
                subject_type=audit_mapping.subject_type,
                subject_id=getattr(event, audit_mapping.subject_id_field),
                correlation_id=self._correlation_id_provider(),
                occurred_at=event.occurred_at,
                details=build_audit_details(event, audit_mapping.subject_id_field),
            )
        )
