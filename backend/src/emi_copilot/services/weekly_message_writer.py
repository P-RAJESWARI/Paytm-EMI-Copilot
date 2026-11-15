"""What the weekly message service needs from a writer: both languages and who wrote each."""

from dataclasses import dataclass
from typing import Protocol

from emi_copilot.domain.reports.weekly_message_template import WeeklyMessageFacts, WeeklyMessages
from emi_copilot.services.ai.ai_flow_types import AiTextSource


@dataclass(frozen=True, slots=True)
class WrittenWeeklyMessages:
    """The week's message in English and Tamil, with who wrote each language."""

    messages: WeeklyMessages
    english_source: AiTextSource
    tamil_source: AiTextSource


class WeeklyMessageWriter(Protocol):
    """Anything that writes one shop's weekly message from the week's report facts."""

    def write(self, merchant_id: str, facts: WeeklyMessageFacts) -> WrittenWeeklyMessages:
        """Gives the shop's message for the facts; the same facts give the same text."""
        ...
