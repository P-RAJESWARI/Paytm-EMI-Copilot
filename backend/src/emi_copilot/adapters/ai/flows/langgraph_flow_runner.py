"""LangGraphAiFlowRunner: runs a flow as a linear LangGraph StateGraph (optional "ai" extra).

This is the only module that imports langgraph, and only when a runner is built, so the rest of
the application imports and runs without it (CLAUDE.md D5, ADR 0025). The graph is linear: one
node per step, edges in order, a conditional edge to END once the state has finished. There are
no cycles, no tool nodes and no prebuilt agents, and every run has an explicit recursion limit.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, override

from emi_copilot.adapters.ai.flows.flow_runner_port import (
    AiFlowDefinition,
    AiFlowRunnerPort,
    AiFlowStep,
    FlowState,
    require_runnable_flow,
)

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

LANGGRAPH_RUNNER_NAME = "langgraph"


class LinearGraphState(TypedDict):
    """The graph's state: the flow state, and the steps of this run (never updated by a node)."""

    flow_state: Any
    steps: tuple[AiFlowStep[Any], ...]


GraphUpdate = dict[str, object]


class LinearGraphNode(Protocol):
    """A node as LangGraph calls it: one argument named state, returning the state update."""

    def __call__(self, state: LinearGraphState) -> GraphUpdate:
        """Runs the node."""
        ...


def build_step_node(step_index: int) -> LinearGraphNode:
    """Gives the node that runs the step at one position and returns only the new flow state."""

    def run_step_node(state: LinearGraphState) -> GraphUpdate:
        """Runs this position's step on the current flow state."""
        return {"flow_state": state["steps"][step_index].run(state["flow_state"])}

    return run_step_node


def build_route(next_node_name: str, end_marker: str) -> Callable[[LinearGraphState], str]:
    """Gives the router that ends the graph once the flow state has finished."""

    def route_after(graph_state: LinearGraphState) -> str:
        """Goes to END for a finished state, otherwise to the next step."""
        flow_state: FlowState = graph_state["flow_state"]
        return end_marker if flow_state.has_finished else next_node_name

    return route_after


def recursion_limit_for(step_count: int) -> int:
    """Gives the explicit limit: one super-step per node plus one, at most 6."""
    return step_count + 1


# Pattern: Strategy. The second interchangeable runtime for the same flow definition; it gives
# the flows a graph shape for later tracing without changing what they compute.
class LangGraphAiFlowRunner(AiFlowRunnerPort):
    """Compiles each flow shape once and invokes it with the flow's steps and an explicit limit."""

    def __init__(self) -> None:
        """Imports langgraph now, so a missing extra fails at startup, not on a customer's tap."""
        from langgraph.graph import END, START, StateGraph  # noqa: PLC0415 - optional extra

        self._state_graph_class = StateGraph
        self._start_marker: str = START
        self._end_marker: str = END
        self._compiled_graphs: dict[tuple[str, tuple[str, ...]], CompiledStateGraph[Any]] = {}

    @property
    @override
    def runner_name(self) -> str:
        """Gives "langgraph"."""
        return LANGGRAPH_RUNNER_NAME

    @override
    def run[StateType: FlowState](
        self, flow: AiFlowDefinition[StateType], initial_state: StateType
    ) -> StateType:
        """Invokes the compiled linear graph; the steps travel in the graph state, not the graph."""
        require_runnable_flow(flow)
        final_graph_state = self._compiled_graph_for(flow).invoke(
            {"flow_state": initial_state, "steps": flow.steps},
            config={"recursion_limit": recursion_limit_for(len(flow.steps))},
        )
        final_state: StateType = final_graph_state["flow_state"]
        return final_state

    def _compiled_graph_for(self, flow: AiFlowDefinition[Any]) -> "CompiledStateGraph[Any]":
        """Gives the graph compiled for this flow's name and step names, compiling it once."""
        shape = (flow.flow_name, flow.step_names)
        if shape not in self._compiled_graphs:
            self._compiled_graphs[shape] = self._compile_linear_graph(flow.step_names)
        return self._compiled_graphs[shape]

    def _compile_linear_graph(self, step_names: tuple[str, ...]) -> "CompiledStateGraph[Any]":
        """Builds START -> step 1 -> ... -> step n -> END, leaving early once finished."""
        graph = self._state_graph_class(LinearGraphState)
        previous_node_name = self._start_marker
        for step_index, step_name in enumerate(step_names):
            graph.add_node(step_name, build_step_node(step_index))
            graph.add_conditional_edges(
                previous_node_name,
                build_route(step_name, self._end_marker),
                [step_name, self._end_marker],
            )
            previous_node_name = step_name
        graph.add_edge(previous_node_name, self._end_marker)
        return graph.compile()
