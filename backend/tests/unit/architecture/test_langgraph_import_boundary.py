"""LangGraph is used only by its flow runner, and LangChain is never imported (ADR 0025)."""

from pathlib import Path

from tests.unit.architecture.source_files import APPLICATION_SOURCE_ROOT, list_application_modules
from tests.unit.architecture.test_import_boundaries import list_imported_module_names

BACKEND_DIRECTORY = APPLICATION_SOURCE_ROOT.parents[1]
LANGGRAPH_RUNNER_FILE = (
    APPLICATION_SOURCE_ROOT / "adapters" / "ai" / "flows" / "langgraph_flow_runner.py"
)
LANGGRAPH_RUNNER_TEST_FILE = (
    BACKEND_DIRECTORY
    / "tests"
    / "unit"
    / "adapters"
    / "ai"
    / "flows"
    / "test_langgraph_flow_runner.py"
)


def top_level_names_imported_by(source_file: Path) -> set[str]:
    """Gives the top-level package of every module a file imports."""
    return {name.split(".", maxsplit=1)[0] for name in list_imported_module_names(source_file)}


def list_backend_python_files() -> list[Path]:
    """Lists the application, script and test modules, the ones a developer writes."""
    return [
        *list_application_modules(),
        *sorted((BACKEND_DIRECTORY / "scripts").rglob("*.py")),
        *sorted((BACKEND_DIRECTORY / "tests").rglob("*.py")),
    ]


def test_only_langgraph_flow_runner_imports_langgraph() -> None:
    """In src/, the runner is the one module importing langgraph; elsewhere only its test does."""
    importing_files = {
        source_file
        for source_file in list_backend_python_files()
        if "langgraph" in top_level_names_imported_by(source_file)
    }
    assert importing_files == {LANGGRAPH_RUNNER_FILE, LANGGRAPH_RUNNER_TEST_FILE}


def test_no_backend_module_imports_langchain() -> None:
    """No LangChain anywhere; langchain-core is only a transitive dependency of langgraph."""
    assert [
        source_file
        for source_file in list_backend_python_files()
        if any(name.startswith("langchain") for name in top_level_names_imported_by(source_file))
    ] == []
