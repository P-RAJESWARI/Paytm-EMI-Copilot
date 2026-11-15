"""SequentialAiFlowRunner: runs a flow in plain Python; the default, with no extra dependency."""

from typing import override

from emi_copilot.adapters.ai.flows.flow_runner_port import (
    AiFlowDefinition,
    AiFlowRunnerPort,
    FlowState,
    require_runnable_flow,
)

SEQUENTIAL_RUNNER_NAME = "sequential"


# Pattern: Strategy. One of two interchangeable runtimes for the same flow definition; this one
# is a plain loop, so the deterministic core runs and is tested without LangGraph.
class SequentialAiFlowRunner(AiFlowRunnerPort):
    """Calls each step in order and stops as soon as a state has finished."""

    @property
    @override
    def runner_name(self) -> str:
        """Gives "sequential"."""
        return SEQUENTIAL_RUNNER_NAME

    @override
    def run[StateType: FlowState](
        self, flow: AiFlowDefinition[StateType], initial_state: StateType
    ) -> StateType:
        """Runs the steps in order; a finished state skips every remaining step."""
        require_runnable_flow(flow)
        state = initial_state
        for step in flow.steps:
            if state.has_finished:
                break
            state = step.run(state)
        return state
