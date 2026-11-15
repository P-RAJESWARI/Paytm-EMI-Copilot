"""Documented problem answers of the customer voice and teach-back operations (Layer 4)."""

from emi_copilot.api.openapi_documentation import ProblemExample

AUDIO_TOO_LARGE_PROBLEM = ProblemExample(
    422,
    "AUDIO_TOO_LARGE",
    "Recording too large",
    "The recording is larger than the upload limit.",
    "The body is larger than SPEECH_UPLOAD_MAX_BYTES (512 KiB by default); record less.",
)
AUDIO_FORMAT_UNSUPPORTED_PROBLEM = ProblemExample(
    422,
    "AUDIO_FORMAT_UNSUPPORTED",
    "Recording format not accepted",
    "Send one recording as audio/webm, ogg, mp4, mpeg or wav.",
    "The body is empty or its Content-Type is not one of the accepted audio types.",
)
SPEECH_UNAVAILABLE_PROBLEM = ProblemExample(
    502,
    "SPEECH_UNAVAILABLE",
    "Speech unavailable",
    "Speech is switched off; type the amount instead.",
    "Speech is switched off, or the speech provider refused or failed; nothing was stored. "
    "The app quietly offers typing instead.",
)
SPEECH_TIMEOUT_PROBLEM = ProblemExample(
    504,
    "SPEECH_TIMEOUT",
    "Speech timed out",
    "The speech provider did not answer in time.",
    "The speech provider did not answer within its timeout; try again or type instead.",
)
EXPLANATION_NOT_FOUND_PROBLEM = ProblemExample(
    404,
    "EXPLANATION_NOT_FOUND",
    "Explanation not found",
    "No explanation with this id was shown to the session.",
    "The explanationId was not shown to this session, or it has expired; ask for the "
    "explanation again.",
)
AI_SESSION_RATE_LIMITED_PROBLEM = ProblemExample(
    429,
    "RATE_LIMITED",
    "Too many requests",
    "Too many voice or teach-back requests for this session; try again after Retry-After.",
    "This phone made too many voice or teach-back requests for the session in this window.",
)
SPEECH_PROBLEMS = (SPEECH_UNAVAILABLE_PROBLEM, SPEECH_TIMEOUT_PROBLEM)
