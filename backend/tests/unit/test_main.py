"""Tests for the application factory."""

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from emi_copilot import main
from emi_copilot.config.settings import ApplicationSettings


def test_create_application_mounts_versioned_routers_under_api_v1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resource routers are served under /api/v1 while /health stays unversioned."""
    example_router = APIRouter()

    @example_router.get("/examples")
    def list_examples() -> list[str]:
        """Returns an empty list so the route can be reached."""
        return []

    monkeypatch.setattr(main, "API_VERSION_1_ROUTERS", (example_router,))
    test_client = TestClient(main.create_application(ApplicationSettings()))
    assert test_client.get("/api/v1/examples").status_code == 200
    assert test_client.get("/examples").status_code == 404
    assert test_client.get("/health").status_code == 200


def test_create_application_passes_lifespan_events_through_the_middleware() -> None:
    """Non-HTTP ASGI events (startup and shutdown) reach the application untouched."""
    with TestClient(main.create_application(ApplicationSettings())) as test_client:
        assert test_client.get("/health").status_code == 200
