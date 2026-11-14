"""Application factory: wires settings, logging, middleware and routers. No business logic."""

from fastapi import APIRouter, FastAPI

from emi_copilot.api.controllers.health_controller import health_router
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.core.id_generator import IdGenerator, UlidIdGenerator
from emi_copilot.core.logging import configure_logging
from emi_copilot.core.request_context import CorrelationIdMiddleware

API_VERSION_1_PREFIX = "/api/v1"

# Resource controllers join this tuple as they are built; /health stays unversioned.
API_VERSION_1_ROUTERS: tuple[APIRouter, ...] = ()


def create_application(
    settings: ApplicationSettings | None = None,
    id_generator: IdGenerator | None = None,
) -> FastAPI:
    """Builds the FastAPI application from settings, with injectable ID generation for tests."""
    active_settings = settings or ApplicationSettings()
    configure_logging(active_settings.log_level)
    application = FastAPI(title="EMI-at-Counter Copilot API", version="0.1.0")
    application.add_middleware(
        CorrelationIdMiddleware, id_generator=id_generator or UlidIdGenerator()
    )
    application.include_router(health_router)
    for versioned_router in API_VERSION_1_ROUTERS:
        application.include_router(versioned_router, prefix=API_VERSION_1_PREFIX)
    return application
