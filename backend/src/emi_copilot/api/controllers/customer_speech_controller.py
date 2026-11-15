"""POST .../speech/transcriptions (C2, C8) and POST .../speech/synthesis (C7): optional voice."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from emi_copilot.api.controllers.customer_problem_examples import (
    CUSTOMER_OPERATION_NOTE,
    SESSION_PROBLEMS,
    SESSION_TOKEN_NOTE,
    describe_customer_problem_responses,
)
from emi_copilot.api.controllers.customer_voice_problem_examples import (
    AI_SESSION_RATE_LIMITED_PROBLEM,
    AUDIO_FORMAT_UNSUPPORTED_PROBLEM,
    AUDIO_TOO_LARGE_PROBLEM,
    EXPLANATION_NOT_FOUND_PROBLEM,
    SPEECH_PROBLEMS,
)
from emi_copilot.api.customer_request_context import (
    CustomerLanguageDependency,
    CustomerSessionCredentialsDependency,
)
from emi_copilot.api.customer_voice_dependencies import CustomerSpeechServiceDependency
from emi_copilot.api.openapi_documentation import MALFORMED_REQUEST_PROBLEM
from emi_copilot.api.rate_limiting import enforce_ai_session_rate_limit
from emi_copilot.dtos.customer_speech_dtos import (
    SpeechSynthesisRequest,
    SpeechTranscriptionResponse,
)
from emi_copilot.services.customer.customer_speech_service import (
    ACCEPTED_AUDIO_MEDIA_TYPES,
    CustomerSpeechService,
    SpeechTranscriptionPurpose,
)

customer_speech_router = APIRouter(tags=["customer voice"])

BINARY_AUDIO_SCHEMA = {"schema": {"type": "string", "format": "binary"}}
NO_STORE_HEADERS = {"Cache-Control": "no-store"}
VOICE_NOTE = (
    "Voice is optional: when isVoiceAvailable is false, or on a 502 or 504, the app offers "
    "typing instead. Audio is held in memory only and never stored or logged. Limited per "
    "client and session (429 with Retry-After). "
)


async def read_recording(request: Request, speech_service: CustomerSpeechService) -> bytes:
    """Reads the raw body in memory, refusing it as soon as it passes the upload limit."""
    declared_length = request.headers.get("content-length", "")
    if declared_length.isdigit():
        speech_service.check_upload_size(int(declared_length))
    recording = bytearray()
    async for chunk in request.stream():
        recording.extend(chunk)
        speech_service.check_upload_size(len(recording))
    return bytes(recording)


@customer_speech_router.post(
    "/customer-sessions/{customerSessionId}/speech/transcriptions",
    summary="Turn the customer's recording into text and an amount",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + VOICE_NOTE + "The body is the raw "
        "recording (audio/webm, ogg, mp4, mpeg or wav; codec parameters allowed). purpose "
        "BUDGET is the C2 monthly amount, TEACH_BACK the C8 answer. Accept-Language picks the "
        "language listened for. recognisedAmountInPaise is the one amount heard (null if none "
        "or several), read deterministically, never by AI. This NEVER changes the budget: the "
        "customer still confirms the amount, which calls PUT .../budget."
    ),
    response_description="What was heard and the amount in it.",
    dependencies=[Depends(enforce_ai_session_rate_limit)],
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": dict.fromkeys(sorted(ACCEPTED_AUDIO_MEDIA_TYPES), BINARY_AUDIO_SCHEMA),
        }
    },
    responses=describe_customer_problem_responses(
        *SESSION_PROBLEMS,
        AUDIO_TOO_LARGE_PROBLEM,
        AUDIO_FORMAT_UNSUPPORTED_PROBLEM,
        AI_SESSION_RATE_LIMITED_PROBLEM,
        *SPEECH_PROBLEMS,
    ),
)
async def transcribe_customer_speech(
    request: Request,
    purpose: Annotated[
        SpeechTranscriptionPurpose, Query(description="BUDGET (C2) or TEACH_BACK (C8).")
    ],
    credentials: CustomerSessionCredentialsDependency,
    language: CustomerLanguageDependency,
    speech_service: CustomerSpeechServiceDependency,
) -> SpeechTranscriptionResponse:
    """Transcribes the recording; the database and the speech call run off the event loop."""
    recording = await read_recording(request, speech_service)
    result = await run_in_threadpool(
        speech_service.transcribe_for_session,
        credentials,
        recording,
        request.headers.get("content-type"),
        purpose,
        language,
    )
    return SpeechTranscriptionResponse.from_result(result)


@customer_speech_router.post(
    "/customer-sessions/{customerSessionId}/speech/synthesis",
    summary="Speak an explanation the customer was shown",
    description=(
        CUSTOMER_OPERATION_NOTE + SESSION_TOKEN_NOTE + VOICE_NOTE + "Speaks exactly the text "
        "of an explanation this session was shown, named by its explanationId from POST "
        ".../explanation; the client never supplies text. Answers the audio bytes (audio/mpeg "
        "from Sarvam, audio/wav from the labelled Mock) with Cache-Control: no-store."
    ),
    response_class=Response,
    response_description="The spoken explanation.",
    dependencies=[Depends(enforce_ai_session_rate_limit)],
    responses={
        200: {"content": {"audio/mpeg": BINARY_AUDIO_SCHEMA, "audio/wav": BINARY_AUDIO_SCHEMA}},
        **describe_customer_problem_responses(
            MALFORMED_REQUEST_PROBLEM,
            *SESSION_PROBLEMS,
            EXPLANATION_NOT_FOUND_PROBLEM,
            AI_SESSION_RATE_LIMITED_PROBLEM,
            *SPEECH_PROBLEMS,
        ),
    },
)
def synthesise_customer_explanation(
    synthesis_request: SpeechSynthesisRequest,
    credentials: CustomerSessionCredentialsDependency,
    speech_service: CustomerSpeechServiceDependency,
) -> Response:
    """Answers the shown explanation as audio that the browser must not cache."""
    audio = speech_service.synthesise_shown_explanation(
        credentials, synthesis_request.explanation_id
    )
    return Response(content=audio.content, media_type=audio.media_type, headers=NO_STORE_HEADERS)
