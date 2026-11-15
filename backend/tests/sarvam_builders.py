"""Test builders for the Sarvam adapters: a scripted in-memory server and fixture loading.

No test ever reaches the network: every client sends through httpx.MockTransport.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from pydantic import SecretStr

from emi_copilot.adapters.ai.sarvam.sarvam_chat_text_adapter import SarvamChatTextAdapter
from emi_copilot.adapters.ai.sarvam.sarvam_http_clients import SINGLE_ATTEMPT_POLICY
from emi_copilot.adapters.ai.sarvam.sarvam_speech_adapter import (
    SarvamSpeechAdapter,
    SarvamSpeechHttpClients,
)
from emi_copilot.config.ai_settings import AiSettings
from emi_copilot.core.circuit_breaker import CircuitBreaker
from emi_copilot.core.resilient_http_client import ResilientHttpClient
from tests.fixed_clock import FixedClock

SYNTHETIC_SARVAM_KEY = "synthetic-sarvam-key-for-tests"  # pragma: allowlist secret
SARVAM_FIXTURE_DIRECTORY = Path(__file__).parent / "contract" / "fixtures" / "sarvam"
TEST_FAILURE_THRESHOLD = 2

# A scripted outcome is a response to answer with or an httpx error class to raise.
ScriptedSarvamOutcome = httpx.Response | type[httpx.RequestError]


def load_sarvam_fixture(file_name: str) -> dict[str, object]:
    """Reads one documented-shape Sarvam body from tests/contract/fixtures/sarvam."""
    document: dict[str, object] = json.loads(
        (SARVAM_FIXTURE_DIRECTORY / file_name).read_text(encoding="utf-8")
    )
    return document


def fixture_response(status_code: int, file_name: str) -> httpx.Response:
    """Builds an answer with a fixture body."""
    return httpx.Response(status_code, json=load_sarvam_fixture(file_name))


@dataclass
class ScriptedSarvamServer:
    """Answers each request with the next scripted outcome; the last one repeats forever."""

    outcomes: Sequence[ScriptedSarvamOutcome]
    received_requests: list[httpx.Request] = field(default_factory=list)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Records the request (its body read in memory), then answers or raises as scripted."""
        request.read()
        self.received_requests.append(request)
        outcome = self.outcomes[min(len(self.received_requests), len(self.outcomes)) - 1]
        if isinstance(outcome, httpx.Response):
            return outcome
        raise outcome("synthetic transport failure", request=request)


@dataclass
class ScriptedSarvamClient:
    """A never-retrying resilient client on a scripted server, with its breaker and clock."""

    client: ResilientHttpClient
    server: ScriptedSarvamServer
    circuit_breaker: CircuitBreaker
    clock: FixedClock


def build_scripted_client(
    outcomes: Sequence[ScriptedSarvamOutcome], dependency_name: str = "sarvam-test"
) -> ScriptedSarvamClient:
    """Builds the client a Sarvam adapter would use, sending to a scripted in-memory server."""
    server = ScriptedSarvamServer(outcomes)
    clock = FixedClock(datetime(2026, 11, 15, 9, 30, tzinfo=UTC))
    circuit_breaker = CircuitBreaker(
        dependency_name=dependency_name,
        failure_threshold=TEST_FAILURE_THRESHOLD,
        open_duration=timedelta(seconds=30),
        clock=clock,
    )
    client = ResilientHttpClient(
        http_client=httpx.Client(transport=httpx.MockTransport(server.handle_request)),
        retry_policy=SINGLE_ATTEMPT_POLICY,
        circuit_breaker=circuit_breaker,
        sleep=lambda _: None,
        random_source=_NeverUsedRandom(),
    )
    return ScriptedSarvamClient(client, server, circuit_breaker, clock)


class _NeverUsedRandom:
    """Random source for a client that never retries, so it is never drawn from."""

    def uniform(self, a: float, b: float) -> float:  # noqa: ARG002 - matches RandomSource
        """Never called: Sarvam calls are sent once."""
        raise AssertionError("a Sarvam call must never be retried")


def build_sarvam_speech_adapter(
    speech_to_text: ScriptedSarvamClient, text_to_speech: ScriptedSarvamClient
) -> SarvamSpeechAdapter:
    """Builds the real speech adapter on two scripted clients with default settings."""
    return SarvamSpeechAdapter(
        AiSettings(),
        SecretStr(SYNTHETIC_SARVAM_KEY),
        SarvamSpeechHttpClients(
            speech_to_text=speech_to_text.client, text_to_speech=text_to_speech.client
        ),
    )


def build_sarvam_chat_text_adapter(chat: ScriptedSarvamClient) -> SarvamChatTextAdapter:
    """Builds the real chat adapter on a scripted client with default settings."""
    return SarvamChatTextAdapter(AiSettings(), SecretStr(SYNTHETIC_SARVAM_KEY), chat.client)
