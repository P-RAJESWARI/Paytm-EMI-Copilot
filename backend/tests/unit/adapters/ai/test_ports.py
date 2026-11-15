"""The AI ports speak in domain terms and offer no way to hand an AI component a tool."""

import dataclasses
import inspect
import re
from pathlib import Path

import pytest

from emi_copilot.adapters.ai.ai_types import AiTextRequest
from emi_copilot.adapters.ai.explanation_text_port import ExplanationTextPort
from emi_copilot.adapters.ai.speech_port import SpeechPort
from tests.unit.architecture.source_files import ADAPTERS_DIRECTORY, describe_source_file
from tests.unit.architecture.test_import_boundaries import (
    is_allowed_import,
    list_imported_module_names,
)

AI_ADAPTERS_DIRECTORY = ADAPTERS_DIRECTORY / "ai"
AI_TYPES_MODULE = "emi_copilot.adapters.ai.ai_types"
TOOL_LIKE_NAME_PATTERN = re.compile(r"(?i)tool|function|callback|action|plugin")


def test_explanation_text_port_write_text_takes_only_the_request() -> None:
    """Rule 1: no tool, function or callback can be passed to an AI text writer."""
    parameter_names = list(inspect.signature(ExplanationTextPort.write_text).parameters)
    assert parameter_names == ["self", "request"]


def test_ai_text_request_has_no_tool_like_field() -> None:
    """The request carries instructions, facts and a language; nothing an AI could call."""
    field_names = [field.name for field in dataclasses.fields(AiTextRequest)]
    assert field_names == ["system_instruction", "structured_facts_json", "language"]
    assert not any(TOOL_LIKE_NAME_PATTERN.search(field_name) for field_name in field_names)


@pytest.mark.parametrize(
    ("method_name", "expected_parameters"),
    [("transcribe", ["self", "audio", "language"]), ("synthesise", ["self", "text", "language"])],
)
def test_speech_port_methods_take_only_audio_or_text_and_a_language(
    method_name: str, expected_parameters: list[str]
) -> None:
    """Speech ports translate between voice and text; they get nothing else."""
    method = getattr(SpeechPort, method_name)
    assert list(inspect.signature(method).parameters) == expected_parameters


@pytest.mark.parametrize(
    "port_file",
    [
        AI_ADAPTERS_DIRECTORY / "speech_port.py",
        AI_ADAPTERS_DIRECTORY / "explanation_text_port.py",
        AI_ADAPTERS_DIRECTORY / "ai_types.py",
    ],
    ids=describe_source_file,
)
def test_ai_ports_import_only_standard_library_domain_and_their_types(port_file: Path) -> None:
    """The ports are in domain terms, like the gateway port; no vendor or library leaks in."""
    assert port_file.is_file()
    disallowed_imports = [
        module_name
        for module_name in list_imported_module_names(port_file)
        if not is_allowed_import(module_name) and module_name != AI_TYPES_MODULE
    ]
    assert disallowed_imports == []
