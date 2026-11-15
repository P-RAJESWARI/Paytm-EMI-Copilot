"""AiUsageLogger: one structured log line per AI call, with usage, latency and a cost estimate.

The line never carries prompt text, completion text, transcripts, audio or keys: only counts,
names and outcomes. Usage fields avoid the word "token", which the log redaction blanks.
"""

import logging
import time
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

AI_CALL_LOG_MESSAGE = "ai call finished"
_COST_QUANTUM = Decimal("0.000001")
_ONE_MILLION = Decimal(1_000_000)
_ONE_THOUSAND = Decimal(1_000)
_SECONDS_PER_MINUTE = Decimal(60)
_MILLISECONDS_PER_SECOND = 1_000

ai_usage_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AiPriceList:
    """Provider prices in rupees, from AiSettings; Decimal, never float. [Verify] with Sarvam."""

    chat_input_in_rupees_per_million: Decimal
    chat_output_in_rupees_per_million: Decimal
    speech_to_text_in_rupees_per_minute: Decimal
    text_to_speech_in_rupees_per_thousand_characters: Decimal


@dataclass(frozen=True, slots=True)
class AiCallUsage:
    """What one AI call used and how it ended; holds no text, audio or personal data."""

    flow: str
    model: str
    latency_ms: int
    model_input_usage_count: int
    model_output_usage_count: int
    outcome: str
    customer_session_id: str | None = None


def measure_elapsed_milliseconds(started_at: float) -> int:
    """Gives the whole milliseconds since a time.perf_counter() reading."""
    return round((time.perf_counter() - started_at) * _MILLISECONDS_PER_SECOND)


class AiUsageLogger:
    """Writes the usage line of each chat, speech-to-text and text-to-speech call."""

    def __init__(self, prices: AiPriceList) -> None:
        """Keeps the price list the cost estimates are computed from."""
        self._prices = prices

    def record_chat_call(self, usage: AiCallUsage) -> None:
        """Logs a chat call; input and output usage are the provider's token counts."""
        cost = (
            Decimal(usage.model_input_usage_count) * self._prices.chat_input_in_rupees_per_million
            + Decimal(usage.model_output_usage_count)
            * self._prices.chat_output_in_rupees_per_million
        ) / _ONE_MILLION
        self._write(usage, cost)

    def record_speech_to_text_call(self, usage: AiCallUsage) -> None:
        """Logs a transcription; input usage is whole seconds of audio, output is characters."""
        cost = (
            Decimal(usage.model_input_usage_count)
            / _SECONDS_PER_MINUTE
            * self._prices.speech_to_text_in_rupees_per_minute
        )
        self._write(usage, cost)

    def record_text_to_speech_call(self, usage: AiCallUsage) -> None:
        """Logs a synthesis; input usage is characters spoken, output is audio bytes."""
        cost = (
            Decimal(usage.model_input_usage_count)
            / _ONE_THOUSAND
            * self._prices.text_to_speech_in_rupees_per_thousand_characters
        )
        self._write(usage, cost)

    def _write(self, usage: AiCallUsage, cost_in_rupees: Decimal) -> None:
        """Writes the one structured line; the cost is a Decimal string rounded to 0.000001."""
        ai_usage_logger.info(
            AI_CALL_LOG_MESSAGE,
            extra={
                "ai_flow": usage.flow,
                "ai_model": usage.model,
                "latency_ms": usage.latency_ms,
                "model_input_usage_count": usage.model_input_usage_count,
                "model_output_usage_count": usage.model_output_usage_count,
                "estimated_cost_in_rupees": str(
                    cost_in_rupees.quantize(_COST_QUANTUM, rounding=ROUND_HALF_UP)
                ),
                "ai_outcome": usage.outcome,
                "customer_session_id": usage.customer_session_id,
            },
        )
