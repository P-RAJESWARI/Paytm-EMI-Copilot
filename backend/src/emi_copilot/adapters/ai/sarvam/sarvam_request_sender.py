"""SarvamRequestSender: sends one Sarvam request exactly once and returns its success answer."""

import time
from dataclasses import dataclass

import httpx

from emi_copilot.adapters.ai.sarvam.sarvam_api_definitions import REQUEST_ID_FIELD
from emi_copilot.adapters.ai.sarvam.sarvam_error_translator import (
    SarvamErrorTranslator,
    SarvamFailureErrors,
    read_json_object,
    read_text_field,
)
from emi_copilot.core.resilient_http_client import ResilientHttpClient
from emi_copilot.core.upstream_errors import UpstreamCallError

HTTP_STATUS_OK = 200
_MILLISECONDS_PER_SECOND = 1_000


@dataclass(frozen=True, slots=True)
class SarvamAnswer:
    """A 200 answer's JSON object with its request id and how long the call took."""

    document: dict[str, object]
    request_id: str | None
    latency_in_milliseconds: int


class SarvamRequestSender:
    """Sends through send_non_idempotent only, so a Sarvam call is never repeated."""

    def __init__(self, translator: SarvamErrorTranslator) -> None:
        """Keeps the translator every failure goes through."""
        self._translator = translator

    def send(
        self,
        http_client: ResilientHttpClient,
        request: httpx.Request,
        dependency_name: str,
        errors: SarvamFailureErrors,
    ) -> SarvamAnswer:
        """Sends once; raises the capability's typed error for any failure or unusable answer."""
        started_at = time.perf_counter()
        try:
            response = http_client.send_non_idempotent(request)
        except UpstreamCallError as upstream_error:
            raise self._translator.translate_upstream_error(
                upstream_error, errors
            ) from upstream_error
        latency_in_milliseconds = round(
            (time.perf_counter() - started_at) * _MILLISECONDS_PER_SECOND
        )
        if response.status_code != HTTP_STATUS_OK:
            raise self._translator.translate_refusal(response, dependency_name, errors)
        document = read_json_object(response)
        if document is None:
            raise self._translator.translate_unusable_answer(errors)
        return SarvamAnswer(
            document=document,
            request_id=read_text_field(document, REQUEST_ID_FIELD),
            latency_in_milliseconds=latency_in_milliseconds,
        )
