"""TeachBackFlow: extract numbers -> score -> template feedback; deterministic and advisory.

The customer's words never reach an AI model (plan Q7): numbers are read with the number audit's
extractor, scored by TeachBackScoringStrategy and answered with template wording. Nothing is
stored, and the result never blocks consent.
"""

from dataclasses import dataclass, replace

from emi_copilot.adapters.ai.flows.flow_runner_port import (
    AiFlowDefinition,
    AiFlowRunnerPort,
    AiFlowStep,
)
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.number_audit import NumberTokenExtractor
from emi_copilot.domain.number_audit.allowed_numbers import whole_rupees_of
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.domain.speech.spoken_amount_parser import read_spoken_numbers
from emi_copilot.domain.teach_back import TeachBackResult, TeachBackScoringStrategy
from emi_copilot.services.ai.ai_flow_types import require_flow_result
from emi_copilot.services.ai.teach_back_feedback import TeachBackFeedback, TeachBackFeedbackWriter

TEACH_BACK_FLOW_NAME = "teach_back"


@dataclass(frozen=True, slots=True)
class TeachBackFlowState:
    """What the teach-back flow knows so far; each step returns a new state."""

    plan: ChosenPlan
    language: CustomerLanguage
    answer_text: str
    stated_numbers: tuple[int, ...] = ()
    result: TeachBackResult = TeachBackResult.TRY_AGAIN
    feedback: TeachBackFeedback | None = None

    @property
    def has_finished(self) -> bool:
        """Tells whether the feedback card is written."""
        return self.feedback is not None


class TeachBackFlow:
    """Checks the customer's own words about the chosen plan and gives advisory feedback."""

    def __init__(
        self,
        flow_runner: AiFlowRunnerPort,
        feedback_writer: TeachBackFeedbackWriter,
        scoring_strategy: TeachBackScoringStrategy | None = None,
    ) -> None:
        """Keeps the runner, the feedback wording and the scoring rule (5% by default)."""
        self._flow_runner = flow_runner
        self._feedback_writer = feedback_writer
        self._scoring_strategy = scoring_strategy or TeachBackScoringStrategy()
        self._extractor = NumberTokenExtractor()
        self._definition = AiFlowDefinition(
            TEACH_BACK_FLOW_NAME,
            (
                AiFlowStep("extract_numbers", self._extract_numbers),
                AiFlowStep("score", self._score),
                AiFlowStep("write_feedback", self._write_feedback),
            ),
        )

    def check(
        self, plan: ChosenPlan, language: CustomerLanguage, answer_text: str
    ) -> TeachBackFeedback:
        """Runs the flow over the customer's answer and gives the feedback card."""
        final_state = self._flow_runner.run(
            self._definition, TeachBackFlowState(plan, language, answer_text)
        )
        return require_flow_result(final_state.feedback, TEACH_BACK_FLOW_NAME)

    def _extract_numbers(self, state: TeachBackFlowState) -> TeachBackFlowState:
        """Reads every number said, composing number words ("three thousand six hundred")."""
        stated_numbers = read_spoken_numbers(self._extractor, state.answer_text)
        return replace(state, stated_numbers=tuple(stated_numbers))

    def _score(self, state: TeachBackFlowState) -> TeachBackFlowState:
        """Scores the numbers against the engine's whole-rupee monthly and the tenure."""
        result = self._scoring_strategy.score(
            state.stated_numbers,
            whole_rupees_of(state.plan.monthly_installment),
            state.plan.tenure_in_months,
        )
        return replace(state, result=result)

    def _write_feedback(self, state: TeachBackFlowState) -> TeachBackFlowState:
        """Writes the template card for the result."""
        feedback = self._feedback_writer.write(
            state.plan, state.language, state.result, state.stated_numbers
        )
        return replace(state, feedback=feedback)
