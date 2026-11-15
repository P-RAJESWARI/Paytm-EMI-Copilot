"""Shared vocabulary of the AI flows: who wrote a text, and why the template was used instead."""

from enum import StrEnum

from emi_copilot.domain.ai_errors import InvalidAiFlowError


class AiTextSource(StrEnum):
    """Who wrote the text the customer or shop sees."""

    AI_AUDITED = "AI_AUDITED"
    TEMPLATE = "TEMPLATE"


class AiFallbackReason(StrEnum):
    """Why the template text was used; recorded as evidence, never shown to anyone."""

    PROVIDER_OFF = "PROVIDER_OFF"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    AUDIT_FAILED = "AUDIT_FAILED"


def require_flow_result[ResultType](result: ResultType | None, flow_name: str) -> ResultType:
    """Gives a finished flow's result; a runner that skipped the last step is a bug and raises."""
    if result is None:
        raise InvalidAiFlowError(f"The flow {flow_name!r} ended without a result.")
    return result
