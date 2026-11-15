"""A text port double that answers each language with a scripted text, or is unavailable."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import override

from emi_copilot.adapters.ai.ai_types import AiTextCompletion, AiTextRequest
from emi_copilot.adapters.ai.explanation_text_port import ExplanationTextPort
from emi_copilot.domain.ai_errors import AiTextUnavailableError
from emi_copilot.domain.customer_sessions import CustomerLanguage

SCRIPTED_INPUT_TOKEN_COUNT = 120
SCRIPTED_OUTPUT_TOKEN_COUNT = 30


@dataclass
class ScriptedExplanationTextPort(ExplanationTextPort):
    """Gives the scripted text of the request's language; a language without one is unavailable."""

    texts_by_language: Mapping[CustomerLanguage, str]
    received_requests: list[AiTextRequest] = field(default_factory=list)

    @override
    def write_text(self, request: AiTextRequest) -> AiTextCompletion:
        """Records the request and answers it as scripted."""
        self.received_requests.append(request)
        text = self.texts_by_language.get(request.language)
        if text is None:
            raise AiTextUnavailableError("No scripted text for this language.")
        return AiTextCompletion(
            text=text,
            model_name="scripted-text",
            input_token_count=SCRIPTED_INPUT_TOKEN_COUNT,
            output_token_count=SCRIPTED_OUTPUT_TOKEN_COUNT,
            finish_reason="stop",
        )
