"""Builds the configured AI flow runner; used only by AiProviderFactory."""

import logging

from emi_copilot.adapters.ai.flows.flow_runner_port import AiFlowRunnerPort
from emi_copilot.adapters.ai.flows.langgraph_flow_runner import LangGraphAiFlowRunner
from emi_copilot.adapters.ai.flows.sequential_flow_runner import SequentialAiFlowRunner
from emi_copilot.config.ai_settings import AiFlowRunnerChoice
from emi_copilot.domain.ai_errors import AiConfigurationError

FLOW_RUNNER_ACTIVE_MESSAGE_TEMPLATE = "AI flow runner active: %s (AI_FLOW_RUNNER)"
LANGGRAPH_MISSING_MESSAGE = (
    "AI_FLOW_RUNNER=langgraph needs the optional 'ai' extra (uv sync --extra ai); "
    "refusing to start. Use AI_FLOW_RUNNER=sequential to run without LangGraph."
)

flow_runner_builder_logger = logging.getLogger(__name__)


def build_flow_runner(choice: AiFlowRunnerChoice) -> AiFlowRunnerPort:
    """Builds the chosen runner and announces it; langgraph without its extra fails startup."""
    if choice is AiFlowRunnerChoice.LANGGRAPH:
        try:
            runner: AiFlowRunnerPort = LangGraphAiFlowRunner()
        except ImportError as missing_extra_error:
            raise AiConfigurationError(LANGGRAPH_MISSING_MESSAGE) from missing_extra_error
    else:
        runner = SequentialAiFlowRunner()
    flow_runner_builder_logger.info(FLOW_RUNNER_ACTIVE_MESSAGE_TEMPLATE, runner.runner_name)
    return runner
