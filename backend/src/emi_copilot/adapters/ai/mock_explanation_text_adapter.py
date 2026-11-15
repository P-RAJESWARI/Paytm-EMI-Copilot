"""MockExplanationTextAdapter: labelled stand-in for the AI text writer (CLAUDE.md rule 10).

Given plan explanation facts it writes two plain sentences from them; any other facts are copied
verbatim. Either way its text carries only numbers the facts hold, so it passes the number audit;
MOCK_AI_TEXT_BEHAVIOUR can make it fail on purpose for tests and demos.
"""

import json
import logging
import re
from types import MappingProxyType

from emi_copilot.adapters.ai.ai_types import AiTextCompletion, AiTextRequest
from emi_copilot.adapters.ai.explanation_text_port import ExplanationTextPort
from emi_copilot.adapters.ai.prompt_facts import ExplanationPromptFacts
from emi_copilot.config.ai_settings import MockAiTextBehaviour
from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.domain.ai_errors import AiTextUnavailableError
from emi_copilot.domain.customer_sessions import CustomerLanguage

MOCK_TEXT_ACTIVE_WARNING_TEMPLATE = (
    "MockExplanationTextAdapter active: AI text is written from the facts, behaviour %s "
    "(MOCK_AI_TEXT_BEHAVIOUR)"
)
MOCK_TEXT_MODEL_NAME = "mock-explanation-text"
MOCK_TEXT_FINISH_REASON = "stop"
OPENING_SENTENCES_BY_LANGUAGE = MappingProxyType(
    {
        CustomerLanguage.ENGLISH: "Here are the plan facts in plain words.",
        # draft: needs native review
        CustomerLanguage.TAMIL: "திட்டத்தின் விவரங்கள் எளிய சொற்களில்.",
    }
)
# {name}, {lender}, {monthly}, {tenure} and {extra} are filled from ExplanationPromptFacts.
EXPLANATION_SENTENCES_BY_LANGUAGE = MappingProxyType(
    {
        CustomerLanguage.ENGLISH: (
            "{name} from {lender}: {monthly} each month for {tenure} months. "
            "The extra you pay in total is {extra}."
        ),
        # draft: needs native review
        CustomerLanguage.TAMIL: (
            "{name} ({lender}): ஒவ்வொரு மாதமும் {monthly}, {tenure} மாதங்களுக்கு. "
            "மொத்தத்தில் நீங்கள் கூடுதலாகச் செலுத்துவது {extra}."
        ),
    }
)
_PAISE_PER_RUPEE = 100
# The first digit of the first rupee amount, else the first digit anywhere in the text.
RUPEE_AMOUNT_FIRST_DIGIT_PATTERN = re.compile(r"₹\s?(?P<digit>[0-9])")
ANY_FIRST_DIGIT_PATTERN = re.compile(r"(?P<digit>[0-9])")
CAMEL_CASE_HUMP_PATTERN = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

mock_text_logger = logging.getLogger(__name__)


def humanise_fact_name(fact_name: str) -> str:
    """Turns a camelCase or snake_case fact name into lower-case words: "monthly amount"."""
    return CAMEL_CASE_HUMP_PATTERN.sub(" ", fact_name).replace("_", " ").lower()


def render_fact_value(fact_value: object) -> str:
    """Gives a text fact exactly as written, and any other fact as compact JSON."""
    if isinstance(fact_value, str):
        return fact_value
    return json.dumps(fact_value, ensure_ascii=False)


def write_explanation(facts: ExplanationPromptFacts, language: CustomerLanguage) -> str:
    """Writes the monthly and extra sentences, amounts formatted as the screens show them."""
    return EXPLANATION_SENTENCES_BY_LANGUAGE[language].format(
        name=facts.plan_display_name,
        lender=facts.lender_label,
        monthly=format_paise_as_whole_rupees(facts.monthly_amount_in_rupees * _PAISE_PER_RUPEE),
        tenure=facts.tenure_in_months,
        extra=format_paise_as_whole_rupees(facts.extra_in_total_in_rupees * _PAISE_PER_RUPEE),
    )


def write_text_from_facts(request: AiTextRequest) -> str:
    """Explains plan facts in two sentences; copies any other facts as "name: value." sentences."""
    facts: dict[str, object] = json.loads(request.structured_facts_json)
    explanation_facts = ExplanationPromptFacts.from_json_object(facts)
    if explanation_facts is not None:
        return write_explanation(explanation_facts, request.language)
    fact_sentences = [
        f"{humanise_fact_name(fact_name)}: {render_fact_value(fact_value)}."
        for fact_name, fact_value in facts.items()
    ]
    return " ".join([OPENING_SENTENCES_BY_LANGUAGE[request.language], *fact_sentences])


def change_one_digit(text: str) -> str:
    """Raises exactly one digit by one (9 becomes 0), preferring the first rupee amount.

    Text without any digit is returned unchanged.
    """
    digit_match = RUPEE_AMOUNT_FIRST_DIGIT_PATTERN.search(text) or ANY_FIRST_DIGIT_PATTERN.search(
        text
    )
    if digit_match is None:
        return text
    position = digit_match.start("digit")
    changed_digit = str((int(text[position]) + 1) % 10)
    return text[:position] + changed_digit + text[position + 1 :]


def count_words(text: str) -> int:
    """Counts whitespace-separated words, the Mock's stand-in for a token count."""
    return len(text.split())


# Pattern: Adapter (Mock). Implements ExplanationTextPort deterministically and offline, so the
# audited explanation flow can be built, tested and demonstrated without the Sarvam key.
class MockExplanationTextAdapter(ExplanationTextPort):
    """Writes text from the request facts; can be told to change a digit or to be unavailable."""

    def __init__(self, behaviour: MockAiTextBehaviour = MockAiTextBehaviour.CORRECT) -> None:
        """Keeps the chosen behaviour and announces, naming it, that AI text is mocked."""
        self._behaviour = behaviour
        mock_text_logger.warning(
            MOCK_TEXT_ACTIVE_WARNING_TEMPLATE,
            behaviour.value,
            extra={"explanation_text_adapter": "mock"},
        )

    def write_text(self, request: AiTextRequest) -> AiTextCompletion:
        """Gives the facts as text, with one digit changed or an error when so configured."""
        if self._behaviour is MockAiTextBehaviour.UNAVAILABLE:
            raise AiTextUnavailableError(
                "MockExplanationTextAdapter is set to be unavailable (MOCK_AI_TEXT_BEHAVIOUR)."
            )
        text = write_text_from_facts(request)
        if self._behaviour is MockAiTextBehaviour.WRONG_NUMBER:
            text = change_one_digit(text)
        return AiTextCompletion(
            text=text,
            model_name=MOCK_TEXT_MODEL_NAME,
            input_token_count=count_words(request.system_instruction)
            + count_words(request.structured_facts_json),
            output_token_count=count_words(text),
            finish_reason=MOCK_TEXT_FINISH_REASON,
        )
