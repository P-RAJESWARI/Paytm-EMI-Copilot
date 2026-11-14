"""Application factory: wires settings, logging, middleware and routers. No business logic."""

from fastapi import APIRouter, FastAPI

from emi_copilot.api.controllers.health_controller import health_router
from emi_copilot.api.controllers.offer_controller import offer_router
from emi_copilot.api.dependencies import build_application_lifespan
from emi_copilot.api.error_handlers import register_error_handlers
from emi_copilot.api.openapi_documentation import install_openapi_schema
from emi_copilot.api.unexpected_error_middleware import UnexpectedErrorMiddleware
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.core.id_generator import IdGenerator, UlidIdGenerator
from emi_copilot.core.logging import configure_logging
from emi_copilot.core.request_context import CorrelationIdMiddleware

API_VERSION_1_PREFIX = "/api/v1"
API_VERSION = "0.1.0"

# Resource controllers join this tuple as they are built; /health stays unversioned.
API_VERSION_1_ROUTERS: tuple[APIRouter, ...] = (offer_router,)


def create_application(
    settings: ApplicationSettings | None = None,
    id_generator: IdGenerator | None = None,
) -> FastAPI:
    """Builds the FastAPI application; its components are built at startup by the lifespan.

    The id generator, injectable for tests, makes correlation ids and every domain id.
    """
    active_settings = settings or ApplicationSettings()
    active_id_generator = id_generator or UlidIdGenerator()
    configure_logging(active_settings.log_level)
    application = FastAPI(
        title="EMI-at-Counter Copilot API",
        version=API_VERSION,
        lifespan=build_application_lifespan(active_settings, active_id_generator),
    )
    # Added first, so it runs inside CorrelationIdMiddleware and a 500 keeps the correlation id.
    application.add_middleware(UnexpectedErrorMiddleware)
    application.add_middleware(CorrelationIdMiddleware, id_generator=active_id_generator)
    register_error_handlers(application)
    application.include_router(health_router)
    for versioned_router in API_VERSION_1_ROUTERS:
        application.include_router(versioned_router, prefix=API_VERSION_1_PREFIX)
    install_openapi_schema(application)
    return application
