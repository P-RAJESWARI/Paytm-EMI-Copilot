"""AiServiceState: the shown-text caches the AI services share across requests."""

from dataclasses import dataclass

from emi_copilot.core.clock import Clock
from emi_copilot.services.ai.audited_weekly_message_writer import (
    WeeklyMessageCache,
    build_weekly_message_cache,
)
from emi_copilot.services.ai.shown_explanation_cache import ShownExplanationCache


@dataclass(frozen=True, slots=True)
class AiServiceState:
    """Built once at startup by the composition root and kept on the application components."""

    shown_explanations: ShownExplanationCache
    weekly_messages: WeeklyMessageCache

    @classmethod
    def build(cls, clock: Clock) -> "AiServiceState":
        """Builds both bounded caches on the injected clock."""
        return cls(ShownExplanationCache(clock), build_weekly_message_cache(clock))
