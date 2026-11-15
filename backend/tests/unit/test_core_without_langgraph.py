"""The deterministic core imports and runs with langgraph and langchain* blocked (CLAUDE.md D5)."""

import os
import subprocess
import sys
from pathlib import Path

CHECK_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_core_without_langgraph.py"


def test_core_application_runs_without_langgraph() -> None:
    """A fresh isolated interpreter builds the app and explains a plan with LangGraph blocked."""
    environment = {**os.environ, "AI_FLOW_RUNNER": "sequential"}
    completed = subprocess.run(  # noqa: S603 - our own script, run with this interpreter
        [sys.executable, "-I", str(CHECK_SCRIPT)],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    assert "runner=sequential source=AI_AUDITED" in completed.stdout
    assert "core-without-langgraph: OK" in completed.stdout
