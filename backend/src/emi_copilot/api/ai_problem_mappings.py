"""Problem mappings of the AI errors (Layer 4), merged into error_handlers.py's lookup.

Kept apart because error_handlers.py is over the soft file limit.

| Error                          | Status | Why                                              |
|--------------------------------|--------|--------------------------------------------------|
| AudioTooLargeError             | 422    | the recording is over SPEECH_UPLOAD_MAX_BYTES    |
| AudioFormatUnsupportedError    | 422    | empty upload or not an accepted audio type       |
| ExplanationNotFoundError       | 404    | not shown to this session, or expired            |
| SpeechUnavailableError         | 502    | speech off, refused or failed; type instead      |
| SpeechTimeoutError             | 504    | the speech provider did not answer in time       |
| AiProviderError (base), text   | 502    | never reaches a client: text falls back          |
| InvalidAiValueError            | 502    | a provider answer was unusable                   |
| InvalidTeachBackInputError     | 422    | a tolerance outside 0 to 1                       |
| AiConfigurationError,          | 500    | a startup or programming error                   |
|   InvalidAiFlowError           |        |                                                  |
"""

from collections.abc import Mapping
from types import MappingProxyType

from emi_copilot.api.problem_mapping import ProblemMapping
from emi_copilot.domain import ai_errors
from emi_copilot.domain.errors import DomainError

AI_PROBLEM_MAPPINGS_BY_ERROR_TYPE: Mapping[type[DomainError], ProblemMapping] = MappingProxyType(
    {
        ai_errors.AudioTooLargeError: ProblemMapping(422, "Recording too large"),
        ai_errors.AudioFormatUnsupportedError: ProblemMapping(422, "Recording format not accepted"),
        ai_errors.ExplanationNotFoundError: ProblemMapping(404, "Explanation not found"),
        ai_errors.AiProviderError: ProblemMapping(502, "AI provider failed"),
        ai_errors.AiTextUnavailableError: ProblemMapping(502, "AI text unavailable"),
        ai_errors.SpeechUnavailableError: ProblemMapping(502, "Speech unavailable"),
        ai_errors.SpeechTimeoutError: ProblemMapping(504, "Speech timed out"),
        ai_errors.SpeechTextTooLongError: ProblemMapping(502, "Speech unavailable"),
        ai_errors.InvalidAiValueError: ProblemMapping(502, "Unusable AI answer"),
        ai_errors.InvalidTeachBackInputError: ProblemMapping(422, "Invalid teach-back input"),
        ai_errors.AiConfigurationError: ProblemMapping(500, "AI configuration invalid"),
        ai_errors.InvalidAiFlowError: ProblemMapping(500, "AI flow invalid"),
    }
)
