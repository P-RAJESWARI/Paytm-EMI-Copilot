"""ExplanationTextPort: writes plain-words text from typed facts (Layer 4)."""

from abc import ABC, abstractmethod

from emi_copilot.adapters.ai.ai_types import AiTextCompletion, AiTextRequest


# Pattern: Port and Adapter. The AI text writer sits beside the money path: it receives facts
# and returns text only. The interface has no tool parameter, so no implementation can be asked
# to call payment, consent or database functions (CLAUDE.md rule 1). Every number it writes is
# audited before anyone sees it (rule 2).
class ExplanationTextPort(ABC):
    """Writes one short text from instructions and facts; the text is untrusted until audited."""

    @abstractmethod
    def write_text(self, request: AiTextRequest) -> AiTextCompletion:
        """Gives the written text and its usage; raises AiTextUnavailableError when it cannot."""
