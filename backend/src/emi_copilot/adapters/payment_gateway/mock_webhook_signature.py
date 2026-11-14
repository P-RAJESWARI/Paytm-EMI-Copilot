"""The Mock gateway's webhook format: four signed text fields and an HMAC-SHA256 signature.

Mock-only, so the payment flow can be exercised end to end with no vendor and no key. The
signature is the lowercase hex HMAC-SHA256, under the adapter's secret, of the canonical form of
every other field: a compact JSON object with keys sorted, so no field value containing a
separator can make two different notifications sign the same bytes.
"""

import hashlib
import hmac
import json
from collections.abc import Mapping

from emi_copilot.domain.errors import WebhookSignatureInvalidError

MOCK_ORDER_ID_FIELD = "orderId"
MOCK_STATUS_FIELD = "status"
MOCK_TRANSACTION_ID_FIELD = "transactionId"
MOCK_AMOUNT_IN_PAISE_FIELD = "amountInPaise"
MOCK_SIGNATURE_FIELD = "signature"
MOCK_SIGNED_FIELD_NAMES = frozenset(
    {
        MOCK_ORDER_ID_FIELD,
        MOCK_STATUS_FIELD,
        MOCK_TRANSACTION_ID_FIELD,
        MOCK_AMOUNT_IN_PAISE_FIELD,
    }
)
MOCK_NOTIFICATION_FIELD_NAMES = MOCK_SIGNED_FIELD_NAMES | {MOCK_SIGNATURE_FIELD}


def build_canonical_signed_text(signed_fields: Mapping[str, str]) -> str:
    """Gives the exact text that is signed: the fields as compact JSON with keys sorted."""
    return json.dumps(
        dict(signed_fields), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def calculate_mock_webhook_signature(signed_fields: Mapping[str, str], secret: bytes) -> str:
    """Signs the canonical text of the fields with HMAC-SHA256 and returns lowercase hex."""
    canonical_text = build_canonical_signed_text(signed_fields)
    return hmac.new(secret, canonical_text.encode("utf-8"), hashlib.sha256).hexdigest()


def require_valid_mock_webhook_signature(received_fields: Mapping[str, str], secret: bytes) -> None:
    """Raises unless exactly the expected fields arrived and the signature matches all of them.

    Only field names are inspected before the signature check; no value other than the signature
    itself is read. The comparison is constant-time, so timing reveals nothing about the secret.
    """
    if set(received_fields) != MOCK_NOTIFICATION_FIELD_NAMES:
        raise WebhookSignatureInvalidError(
            "The notification does not carry exactly the signed fields and a signature."
        )
    signed_fields = {
        field_name: received_fields[field_name] for field_name in MOCK_SIGNED_FIELD_NAMES
    }
    expected_signature = calculate_mock_webhook_signature(signed_fields, secret)
    received_signature = received_fields[MOCK_SIGNATURE_FIELD]
    if not hmac.compare_digest(
        expected_signature.encode("utf-8"), received_signature.encode("utf-8")
    ):
        raise WebhookSignatureInvalidError("The notification signature does not match its fields.")
