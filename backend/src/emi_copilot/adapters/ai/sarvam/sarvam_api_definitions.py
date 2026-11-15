"""Sarvam AI API facts (docs.sarvam.ai, checked 15 Nov 2026); every Sarvam name stays in sarvam/.

Only the documented fields listed in the Layer 4 plan are sent. Anything not confirmed with the
real key is marked [Verify]; scripts/sarvam_smoke_check.py (step 4.8) clears those items.
"""

from types import MappingProxyType

from emi_copilot.domain.customer_sessions import CustomerLanguage

SPEECH_TO_TEXT_PATH = "/speech-to-text"
TEXT_TO_SPEECH_PATH = "/text-to-speech"
CHAT_COMPLETIONS_PATH = "/v1/chat/completions"
SUBSCRIPTION_KEY_HEADER = "api-subscription-key"

SPEECH_TO_TEXT_DEPENDENCY_NAME = "sarvam-speech-to-text"
TEXT_TO_SPEECH_DEPENDENCY_NAME = "sarvam-text-to-speech"
CHAT_DEPENDENCY_NAME = "sarvam-chat"

LANGUAGE_CODES_BY_LANGUAGE = MappingProxyType(
    {CustomerLanguage.ENGLISH: "en-IN", CustomerLanguage.TAMIL: "ta-IN"}
)

# Text-to-speech refuses longer text; we refuse it first so no credit is spent on a 4xx.
TEXT_TO_SPEECH_MAXIMUM_CHARACTERS = 2_500
TEXT_TO_SPEECH_OUTPUT_AUDIO_CODEC = "mp3"
TEXT_TO_SPEECH_MEDIA_TYPE = "audio/mpeg"

# The error body is {"error": {"message", "code", "request_id"}} (verified 2026-11-15); only the
# code and request id are read, never the message.
ERROR_OBJECT_FIELD = "error"
ERROR_CODE_FIELD = "code"
REQUEST_ID_FIELD = "request_id"
INSUFFICIENT_QUOTA_ERROR_CODE = "insufficient_quota_error"
