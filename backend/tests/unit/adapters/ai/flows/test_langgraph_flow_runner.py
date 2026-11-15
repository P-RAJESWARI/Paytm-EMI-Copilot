"""Both flow runners: same order, early stop, explicit recursion limit, refused flow shapes."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

import pytest
from langgraph.graph.state import CompiledStateGraph, StateGraph

from emi_copilot.adapters.ai.flows.flow_runner_port import (
    MAXIMUM_FLOW_STEPS,
    MAXIMUM_RECURSION_LIMIT,
    AiFlowDefinition,
    AiFlowRunnerPort,
    AiFlowStep,
)
from emi_copilot.adapters.ai.flows.langgraph_flow_runner import LangGraphAiFlowRunner
from emi_copilot.adapters.ai.flows.sequential_flow_runner import SequentialAiFlowRunner
from emi_copilot.domain.ai_errors import InvalidAiFlowError

RUNNER_BUILDERS: dict[str, Callable[[], AiFlowRunnerPort]] = {
    "sequential": SequentialAiFlowRunner,
    "langgraph": LangGraphAiFlowRunner,
}


@dataclass(frozen=True, slots=True)
class VisitState:
    """A test state that records which steps ran."""

    visited_steps: tuple[str, ...] = ()
    has_finished: bool = False


def visit(step_name: str, *, finishes: bool = False) -> AiFlowStep[VisitState]:
    """Builds a step that records its name and may finish the flow."""

    def run_visit(state: VisitState) -> VisitState:
        """Returns a new state with this step recorded."""
        return replace(
            state, visited_steps=(*state.visited_steps, step_name), has_finished=finishes
        )

    return AiFlowStep(step_name, run_visit)


def build_flow(*steps: AiFlowStep[VisitState]) -> AiFlowDefinition[VisitState]:
    """Builds a test flow of the given steps."""
    return AiFlowDefinition("visit_flow", steps)


@pytest.fixture(params=sorted(RUNNER_BUILDERS))
def runner(request: pytest.FixtureRequest) -> AiFlowRunnerPort:
    """Gives each runner in turn."""
    runner_name: str = request.param
    return RUNNER_BUILDERS[runner_name]()


def test_flow_runner_runs_every_step_in_order(runner: AiFlowRunnerPort) -> None:
    """Steps run once each, in the defined order, and the initial state is left unchanged."""
    initial_state = VisitState()
    final_state = runner.run(
        build_flow(visit("write"), visit("audit"), visit("choose")), initial_state
    )
    assert final_state.visited_steps == ("write", "audit", "choose")
    assert initial_state.visited_steps == ()


def test_langgraph_flow_runner_stops_at_first_finished_step(runner: AiFlowRunnerPort) -> None:
    """A step that finishes the flow (provider off, say) ends it; later steps never run."""
    flow = build_flow(visit("write", finishes=True), visit("audit"), visit("choose"))
    assert runner.run(flow, VisitState()).visited_steps == ("write",)


def test_flow_runner_with_an_already_finished_state_runs_no_step(runner: AiFlowRunnerPort) -> None:
    """A finished state goes straight to the end."""
    final_state = runner.run(build_flow(visit("write")), VisitState(has_finished=True))
    assert final_state.visited_steps == ()


def test_langgraph_flow_runner_refuses_more_than_maximum_steps(runner: AiFlowRunnerPort) -> None:
    """Six steps would need a recursion limit of 7, above the cap of 6, so they are refused."""
    too_many_steps = tuple(visit(f"step_{index}") for index in range(MAXIMUM_FLOW_STEPS + 1))
    with pytest.raises(InvalidAiFlowError, match="at most 5"):
        runner.run(build_flow(*too_many_steps), VisitState())


@pytest.mark.parametrize(
    "flow",
    [build_flow(), build_flow(visit("write"), visit("write"))],
    ids=["no steps", "repeated step name"],
)
def test_flow_runner_refuses_an_empty_flow_or_repeated_step_names(
    runner: AiFlowRunnerPort, flow: AiFlowDefinition[VisitState]
) -> None:
    """Every node needs a unique name, and a flow needs at least one step."""
    with pytest.raises(InvalidAiFlowError):
        runner.run(flow, VisitState())


def test_langgraph_flow_runner_passes_recursion_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """The limit is the step count plus one: 4 for a 3-step flow, and the cap of 6 for 5 steps."""
    received_limits: list[int] = []
    original_invoke = CompiledStateGraph.invoke

    def spy_invoke(
        graph: CompiledStateGraph[Any],
        *arguments: Any,  # noqa: ANN401 - mirrors the real invoke
        **keyword_arguments: Any,  # noqa: ANN401 - mirrors the real invoke
    ) -> Any:  # noqa: ANN401 - mirrors the real invoke
        """Records the recursion limit, then invokes the real graph."""
        received_limits.append(keyword_arguments["config"]["recursion_limit"])
        return original_invoke(graph, *arguments, **keyword_arguments)

    monkeypatch.setattr(CompiledStateGraph, "invoke", spy_invoke)
    runner = LangGraphAiFlowRunner()
    runner.run(build_flow(visit("a"), visit("b"), visit("c")), VisitState())
    longest_flow = build_flow(*(visit(f"step_{index}") for index in range(MAXIMUM_FLOW_STEPS)))
    assert len(runner.run(longest_flow, VisitState()).visited_steps) == MAXIMUM_FLOW_STEPS
    assert received_limits == [4, MAXIMUM_RECURSION_LIMIT]


def test_langgraph_flow_runner_compiles_each_flow_shape_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The graph is compiled on first use and reused; the steps travel with each run."""
    compile_count = 0
    original_compile = StateGraph.compile

    def counting_compile(
        graph: StateGraph[Any],
        *arguments: Any,  # noqa: ANN401 - mirrors the real compile
        **keyword_arguments: Any,  # noqa: ANN401 - mirrors the real compile
    ) -> Any:  # noqa: ANN401 - mirrors the real compile
        """Counts compilations, then compiles the real graph."""
        nonlocal compile_count
        compile_count += 1
        return original_compile(graph, *arguments, **keyword_arguments)

    monkeypatch.setattr(StateGraph, "compile", counting_compile)
    runner = LangGraphAiFlowRunner()
    for finishing_step in ("write", "audit"):
        flow = build_flow(visit("write", finishes=finishing_step == "write"), visit("audit"))
        runner.run(flow, VisitState())
    assert compile_count == 1


@pytest.mark.parametrize(("runner_name", "runner_builder"), sorted(RUNNER_BUILDERS.items()))
def test_flow_runner_names_itself(
    runner_name: str, runner_builder: Callable[[], AiFlowRunnerPort]
) -> None:
    """The startup log and traces name the runner."""
    assert runner_builder().runner_name == runner_name
