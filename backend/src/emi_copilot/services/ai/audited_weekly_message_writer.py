"""AuditedWeeklyMessageWriter: the shop's weekly message, AI-written and audited per language."""

import hashlib
import logging
import time
from datetime import date, timedelta

from emi_copilot.core.bounded_timed_cache import BoundedTimedCache
from emi_copilot.core.clock import Clock
from emi_copilot.domain.errors import DomainError
from emi_copilot.domain.reports.weekly_message_template import (
    WeeklyMessageFacts,
    WeeklyMessages,
    WeeklyMessageTemplate,
)
from emi_copilot.services.ai.ai_flow_types import AiFallbackReason, AiTextSource
from emi_copilot.services.ai.ai_usage_logger import (
    AiCallUsage,
    AiUsageLogger,
    measure_elapsed_milliseconds,
)
from emi_copilot.services.ai.weekly_message_flow import (
    WEEKLY_MESSAGE_FLOW_NAME,
    WeeklyLanguageResult,
    WeeklyMessageFlow,
)
from emi_copilot.services.weekly_message_writer import WrittenWeeklyMessages

WEEKLY_MESSAGE_CACHE_MAXIMUM_ENTRIES = 500
WEEKLY_MESSAGE_CACHE_LIFETIME = timedelta(hours=12)
UNKNOWN_MODEL_NAME = "unknown"

WeeklyMessageCacheKey = tuple[str, date, str]
WeeklyMessageCache = BoundedTimedCache[WeeklyMessageCacheKey, WrittenWeeklyMessages]

audited_weekly_message_logger = logging.getLogger(__name__)


def build_weekly_message_cache(clock: Clock) -> WeeklyMessageCache:
    """Builds the bounded cache of shown weekly messages on the injected clock."""
    return BoundedTimedCache(
        clock, WEEKLY_MESSAGE_CACHE_MAXIMUM_ENTRIES, WEEKLY_MESSAGE_CACHE_LIFETIME
    )


def fingerprint_weekly_facts(facts: WeeklyMessageFacts) -> str:
    """Gives a stable digest of the facts, so new report numbers give a new message."""
    return hashlib.sha256(repr(facts).encode()).hexdigest()


# Pattern: Decorator. Wraps the Layer 2 WeeklyMessageTemplate with AI text that must pass the
# number audit, per language; a language that fails keeps the template text.
class AuditedWeeklyMessageWriter:
    """Writes the weekly message once per (shop, week, facts) and repeats exactly that text.

    A repeat read and "send" therefore use the text that was shown, and no second paid AI call
    is made. No AI error ever escapes: any failure gives the template text.
    """

    def __init__(
        self,
        weekly_message_flow: WeeklyMessageFlow,
        template: WeeklyMessageTemplate,
        cache: WeeklyMessageCache,
        usage_logger: AiUsageLogger,
    ) -> None:
        """Keeps the flow, the template fallback, the shown-text cache and the usage logger."""
        self._weekly_message_flow = weekly_message_flow
        self._template = template
        self._cache = cache
        self._usage_logger = usage_logger

    def write(self, merchant_id: str, facts: WeeklyMessageFacts) -> WrittenWeeklyMessages:
        """Gives the cached message for these facts, or writes, audits and remembers it."""
        cache_key = (merchant_id, facts.period.period_start_date, fingerprint_weekly_facts(facts))
        cached = self._cache.find(cache_key)
        if cached is not None:
            return cached
        written = self._write_now(facts)
        self._cache.store(cache_key, written)
        return written

    def _write_now(self, facts: WeeklyMessageFacts) -> WrittenWeeklyMessages:
        """Runs the flow; an unexpected flow error gives both template languages."""
        started_at = time.perf_counter()
        try:
            result = self._weekly_message_flow.write(facts)
        except DomainError as error:
            audited_weekly_message_logger.warning(
                "weekly message flow failed; template text used", extra={"error_code": error.code}
            )
            return WrittenWeeklyMessages(
                self._template.render(facts), AiTextSource.TEMPLATE, AiTextSource.TEMPLATE
            )
        latency_ms = measure_elapsed_milliseconds(started_at)
        for language_result in (result.english, result.tamil):
            self._record_usage(language_result, latency_ms)
        return WrittenWeeklyMessages(
            WeeklyMessages(result.english.message, result.tamil.message),
            result.english.source,
            result.tamil.source,
        )

    def _record_usage(self, language_result: WeeklyLanguageResult, latency_ms: int) -> None:
        """Logs one language's AI call; latency is the whole flow's, as both run in one flow."""
        if language_result.fallback_reason is AiFallbackReason.PROVIDER_OFF:
            return
        self._usage_logger.record_chat_call(
            AiCallUsage(
                flow=WEEKLY_MESSAGE_FLOW_NAME,
                model=language_result.model_name or UNKNOWN_MODEL_NAME,
                latency_ms=latency_ms,
                model_input_usage_count=language_result.input_token_count,
                model_output_usage_count=language_result.output_token_count,
                outcome=(language_result.fallback_reason or language_result.source).value,
            )
        )
