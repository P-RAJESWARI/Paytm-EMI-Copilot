"""Translates failed Sarvam calls into typed AI errors; raw vendor payloads never leave sarvam/.

Only the HTTP status, Sarvam's short error code and its request id are logged, never the message,
the request or the key. Every failure is one the caller answers with its fallback.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from emi_copilot.adapters.ai.sarvam.sarvam_api_definitions import (
    ERROR_CODE_FIELD,
    ERROR_OBJECT_FIELD,
    INSUFFICIENT_QUOTA_ERROR_CODE,
    REQUEST_ID_FIELD,
)
from emi_copilot.core.upstream_errors import (
    CircuitOpenError,
    UpstreamCallError,
    UpstreamTimeoutError,
)
from emi_copilot.domain.ai_errors import (
    AiProviderError,
    AiTextUnavailableError,
    SpeechTimeoutError,
    SpeechUnavailableError,
)

HTTP_STATUS_FORBIDDEN = 403
HTTP_STATUS_TOO_MANY_REQUESTS = 429

sarvam_error_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SarvamFailureErrors:
    """Which typed error a capability raises when Sarvam is unavailable or too slow."""

    unavailable: Callable[[str], AiProviderError]
    timeout: Callable[[str], AiProviderError]


SPEECH_FAILURE_ERRORS = SarvamFailureErrors(
    unavailable=SpeechUnavailableError, timeout=SpeechTimeoutError
)
CHAT_FAILURE_ERRORS = SarvamFailureErrors(
    unavailable=AiTextUnavailableError, timeout=AiTextUnavailableError
)


def read_json_object(response: httpx.Response) -> dict[str, object] | None:
    """Gives the response body as a JSON object, or None when it is not one."""
    try:
        document = response.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return document if isinstance(document, dict) else None


def read_text_field(document: dict[str, object] | None, field_name: str) -> str | None:
    """Gives one text field of a JSON object, or None when it is missing or not text."""
    value = None if document is None else document.get(field_name)
    return value if isinstance(value, str) else None


def read_error_object(response: httpx.Response) -> dict[str, object] | None:
    """Gives the documented {"error": {...}} object of a refusal [Verify], or None."""
    error_object = (read_json_object(response) or {}).get(ERROR_OBJECT_FIELD)
    return error_object if isinstance(error_object, dict) else None


def describe_refusal(status_code: int, error_code: str | None) -> str:
    """Gives our own English reason for a 4xx; never Sarvam's message."""
    if error_code == INSUFFICIENT_QUOTA_ERROR_CODE:
        return "Sarvam credits are used up (insufficient_quota_error)."
    if status_code == HTTP_STATUS_FORBIDDEN:
        return "Sarvam refused the API key (403); check SARVAM_API_KEY."
    if status_code == HTTP_STATUS_TOO_MANY_REQUESTS:
        return "Sarvam rate limit reached (429)."
    return f"Sarvam refused the call with status {status_code}."


# Pattern: Adapter (error side). One place turns transport failures and Sarvam refusals into
# typed AI errors, so services never see an HTTP status or a Sarvam payload.
class SarvamErrorTranslator:
    """Maps core upstream errors and non-success Sarvam answers to the capability's errors."""

    def translate_upstream_error(
        self, error: UpstreamCallError, errors: SarvamFailureErrors
    ) -> AiProviderError:
        """Turns a timeout, an open breaker, a 5xx or a broken transport into a typed error."""
        if isinstance(error, UpstreamTimeoutError):
            return errors.timeout("Sarvam did not answer in time.")
        if isinstance(error, CircuitOpenError):
            return errors.unavailable("The Sarvam circuit is open; nothing was sent.")
        return errors.unavailable("Sarvam could not serve the call.")

    def translate_refusal(
        self, response: httpx.Response, dependency_name: str, errors: SarvamFailureErrors
    ) -> AiProviderError:
        """Turns a 4xx answer into a typed error, logging only its status, code and request id."""
        error_object = read_error_object(response)
        error_code = read_text_field(error_object, ERROR_CODE_FIELD)
        sarvam_error_logger.warning(
            "sarvam call refused",
            extra={
                "dependency_name": dependency_name,
                "http_status_code": response.status_code,
                "sarvam_error_code": error_code,
                "sarvam_request_id": read_text_field(error_object, REQUEST_ID_FIELD),
            },
        )
        return errors.unavailable(describe_refusal(response.status_code, error_code))

    def translate_unusable_answer(self, errors: SarvamFailureErrors) -> AiProviderError:
        """Builds the error for a success answer whose body lacks the documented fields."""
        return errors.unavailable("Sarvam answered without the documented fields.")
