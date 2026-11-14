"""Liveness endpoint used by local tooling and container orchestrators."""

from fastapi import APIRouter

from emi_copilot.api.openapi_documentation import describe_problem_responses
from emi_copilot.dtos.health_dto import HealthResponse

health_router = APIRouter(tags=["health"])


@health_router.get(
    "/health",
    summary="Liveness check",
    description="Returns ok while the process can serve requests. Unauthenticated.",
    responses=describe_problem_responses(),
)
def get_health() -> HealthResponse:
    """Reports that the application process is up."""
    return HealthResponse(status="ok")
