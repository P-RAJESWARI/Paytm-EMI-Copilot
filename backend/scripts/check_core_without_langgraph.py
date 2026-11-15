"""Proves the deterministic core imports and runs with LangGraph and LangChain unavailable.

Run with `python -I` (make core-without-langgraph, and a pytest test, do): an import blocker
refuses langgraph and every langchain* module, then the application is built through its
factory and the explanation flow runs with the Mock text adapter and the sequential runner
(CLAUDE.md D5: the core runs and is tested without LangGraph).
"""

import os
import sys
import warnings
from collections.abc import Sequence
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from emi_copilot.domain.sales import ChosenPlan

SUCCESS_LINE = "core-without-langgraph: OK"
# Every AI variable the check sets itself, so a developer's .env (and its key) cannot change it.
AI_ENVIRONMENT_FOR_THE_CHECK = {
    "AI_FLOW_RUNNER": "sequential",
    "SPEECH_PROVIDER_MODE": "mock",
    "EXPLANATION_TEXT_PROVIDER_MODE": "mock",
    "MOCK_AI_TEXT_BEHAVIOUR": "correct",
}


def is_blocked_module(module_name: str) -> bool:
    """Tells whether a module belongs to langgraph or to any langchain* package."""
    top_level_name = module_name.split(".", maxsplit=1)[0]
    return top_level_name == "langgraph" or top_level_name.startswith("langchain")


class LangGraphImportBlocker(MetaPathFinder):
    """Makes every import of langgraph or langchain* fail as if the package were not installed."""

    @override
    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        """Refuses a blocked module; leaves every other import to the normal finders."""
        if is_blocked_module(fullname):
            raise ModuleNotFoundError(f"{fullname} is blocked by this check", name=fullname)
        return None


def build_design_plan_a() -> "ChosenPlan":
    """Builds the design's plan A on ₹22,000: no-cost, ₹3,666.67 for 6 months, nothing extra."""
    from emi_copilot.domain.money import Money  # noqa: PLC0415
    from emi_copilot.domain.payments import EmiType  # noqa: PLC0415
    from emi_copilot.domain.sales import ChosenPlan  # noqa: PLC0415

    return ChosenPlan(
        offer_id="offer-plan-a",
        plan_kind=EmiType.NO_COST,
        lender_label="Brand",
        tenure_in_months=6,
        monthly_installment=Money.from_rupees("3666.67"),
        extra_in_total=Money.from_paise(0),
        total_payable=Money.from_rupees("22000"),
    )


def run_core_with_the_mock_text_adapter() -> str:
    """Builds the application, then explains design plan A through the sequential flow."""
    # Imported here, after the blocker is installed, so any LangGraph import in them would fail.
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from emi_copilot.config.settings import ApplicationSettings  # noqa: PLC0415
    from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees  # noqa: PLC0415
    from emi_copilot.domain.customer_sessions import CustomerLanguage  # noqa: PLC0415
    from emi_copilot.main import create_application  # noqa: PLC0415
    from emi_copilot.services.ai.explanation_flow import ExplanationFlow  # noqa: PLC0415
    from emi_copilot.services.customer.template_explanation_service import (  # noqa: PLC0415
        TemplateExplanationService,
    )

    application = create_application(ApplicationSettings())
    with TestClient(application):
        ai_components = application.state.application_components.ai
        flow = ExplanationFlow(
            ai_components.explanation_text,
            ai_components.flow_runner,
            TemplateExplanationService(format_paise_as_whole_rupees),
        )
        result = flow.explain(build_design_plan_a(), CustomerLanguage.ENGLISH)
        runner_name: str = ai_components.flow_runner.runner_name
    return f"runner={runner_name} source={result.source.value} text={result.text}"


def main() -> int:
    """Runs the check; exits non-zero if the flow fails or a blocked module was loaded anyway."""
    sys.meta_path.insert(0, LangGraphImportBlocker())
    # The same known Starlette notice that pytest's configuration ignores (ADR 0008: httpx).
    warnings.filterwarnings("ignore", message="Using `httpx` with `starlette.testclient`")
    os.environ.pop("SARVAM_API_KEY", None)
    os.environ.update(AI_ENVIRONMENT_FOR_THE_CHECK)
    summary = run_core_with_the_mock_text_adapter()
    loaded_blocked_modules = sorted(name for name in sys.modules if is_blocked_module(name))
    if loaded_blocked_modules or "source=AI_AUDITED" not in summary:
        sys.stderr.write(f"core-without-langgraph FAILED: {summary} {loaded_blocked_modules}\n")
        return 1
    sys.stdout.write(f"{summary}\nno langgraph or langchain module loaded\n{SUCCESS_LINE}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
