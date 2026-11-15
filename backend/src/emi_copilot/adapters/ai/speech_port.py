"""SpeechPort: turns the customer's voice into text and shown text into speech (Layer 4)."""

from abc import ABC, abstractmethod

from emi_copilot.adapters.ai.ai_types import SpeechAudio, SpeechTranscript, SynthesisedAudio
from emi_copilot.domain.customer_sessions import CustomerLanguage


# Pattern: Port and Adapter. Services speak through this interface, so Sarvam and the labelled
# Mock are interchangeable and tests need no network. Voice is optional: callers always have a
# typed fallback when a SpeechUnavailableError is raised.
class SpeechPort(ABC):
    """Transcribes and synthesises speech in English or Tamil; audio stays in memory only."""

    @abstractmethod
    def transcribe(self, audio: SpeechAudio, language: CustomerLanguage) -> SpeechTranscript:
        """Gives the text of the recording; raises SpeechUnavailableError when it cannot."""

    @abstractmethod
    def synthesise(self, text: str, language: CustomerLanguage) -> SynthesisedAudio:
        """Gives speech for text already shown on screen; raises SpeechUnavailableError."""
