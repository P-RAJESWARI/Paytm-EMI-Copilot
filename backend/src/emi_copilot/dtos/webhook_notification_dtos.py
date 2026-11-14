"""Wire form of a gateway webhook: raw text fields, handed on unread as an untrusted notice."""

from collections.abc import Mapping

from emi_copilot.domain.payments import UnverifiedWebhookNotification


def build_unverified_notification(raw_fields: Mapping[str, str]) -> UnverifiedWebhookNotification:
    """Wraps the received fields, unread, so only the gateway port can verify and read them."""
    return UnverifiedWebhookNotification(received_fields=raw_fields)
