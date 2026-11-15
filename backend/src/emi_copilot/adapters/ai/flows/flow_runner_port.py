"""AiFlowRunnerPort: runs a typed, linear AI flow; the flow never depends on how it is run.

A flow is an ordered tuple of named steps, each a pure function from state to new state. A step
may finish the flow early (has_finished), for example when AI text is unavailable and the
template is already chosen. There are no cycles and no tool-calling steps (owner rule, ADR 0025).
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from emi_copilot.domain.ai_errors import InvalidAiFlowError

MAXIMUM_RECURSION_LIMIT = 6
"""The cap on LangGraph's recursion_limit (plan step 4.5)."""

MAXIMUM_FLOW_STEPS = MAXIMUM_RECURSION_LIMIT - 1
"""A linear graph of n steps needs a recursion limit of n + 1, so the cap of 6 allows 5 steps."""


class FlowState(Protocol):
    """Any frozen flow state; has_finished tells the runners to stop before the next step."""

    @property
    def has_finished(self) -> bool:
        """Tells whether the flow's result is decided, so no further step may run."""
        ...


@dataclass(frozen=True, slots=True)
class AiFlowStep[StateType: FlowState]:
    """One named step: a function that returns a new state and never mutates the old one."""

    name: str
    run: Callable[[StateType], StateType]


@dataclass(frozen=True, slots=True)
class AiFlowDefinition[StateType: FlowState]:
    """A named, linear sequence of steps; every runner runs it the same way."""

    flow_name: str
    steps: tuple[AiFlowStep[StateType], ...]

    @property
    def step_names(self) -> tuple[str, ...]:
        """Gives the step names in order; together with the flow name they identify its shape."""
        return tuple(step.name for step in self.steps)


def require_runnable_flow[StateType: FlowState](flow: AiFlowDefinition[StateType]) -> None:
    """Refuses an empty flow, repeated step names, or more than MAXIMUM_FLOW_STEPS steps."""
    if not flow.steps:
        raise InvalidAiFlowError(f"The flow {flow.flow_name!r} has no steps.")
    if len(set(flow.step_names)) != len(flow.steps):
        raise InvalidAiFlowError(f"The flow {flow.flow_name!r} repeats a step name.")
    if len(flow.steps) > MAXIMUM_FLOW_STEPS:
        raise InvalidAiFlowError(
            f"The flow {flow.flow_name!r} has {len(flow.steps)} steps; at most "
            f"{MAXIMUM_FLOW_STEPS} are allowed."
        )


# Pattern: Port and Adapter. Services run their flows through this interface, so the plain
# sequential runner and the optional LangGraph runner are interchangeable (CLAUDE.md D5).
class AiFlowRunnerPort(ABC):
    """Runs a flow definition from an initial state and gives the final state."""

    @property
    @abstractmethod
    def runner_name(self) -> str:
        """Gives the short, stable name of this runner, such as "sequential"."""

    @abstractmethod
    def run[StateType: FlowState](
        self, flow: AiFlowDefinition[StateType], initial_state: StateType
    ) -> StateType:
        """Runs the steps in order and stops at the first finished state."""
