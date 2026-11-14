"""Application factory: wires settings, logging, middleware and routers. No business logic."""

import logging

from fastapi import APIRouter, FastAPI

from emi_copilot.api.controllers.health_controller import health_router
from emi_copilot.api.controllers.merchant_controller import merchant_router
from emi_copilot.api.controllers.mock_customer_simulator_controller import (
    mock_customer_simulator_router,
)
from emi_copilot.api.controllers.offer_controller import offer_router
from emi_copilot.api.controllers.payment_link_controller import payment_link_router
from emi_copilot.api.controllers.payment_status_controller import payment_status_router
from emi_copilot.api.controllers.paytm_webhook_controller import paytm_webhook_router
from emi_copilot.api.controllers.product_controller import product_router
from emi_copilot.api.controllers.report_controller import report_router
from emi_copilot.api.controllers.sale_controller import sale_router
from emi_copilot.api.controllers.sale_event_stream_controller import sale_event_stream_router
from emi_copilot.api.controllers.sale_handoff_controller import sale_handoff_router
from emi_copilot.api.controllers.weekly_message_controller import weekly_message_router
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
MOCK_CUSTOMER_SIMULATOR_ACTIVE_WARNING = (
    "MockCustomerSimulator active: demo endpoints play the customer agreeing and paying"
)

application_factory_logger = logging.getLogger(__name__)

# Resource controllers join this tuple as they are built; /health stays unversioned.
API_VERSION_1_ROUTERS: tuple[APIRouter, ...] = (
    offer_router,
    payment_link_router,
    payment_status_router,
    paytm_webhook_router,
    merchant_router,
    product_router,
    # Before sale_router: /sales/events must not be matched as /sales/{saleId}.
    sale_event_stream_router,
    sale_router,
    sale_handoff_router,
    report_router,
    weekly_message_router,
)


def mount_mock_customer_simulator(application: FastAPI) -> None:
    """Mounts the labelled demo simulator under /api/v1 and announces it (rule 10)."""
    application.include_router(mock_customer_simulator_router, prefix=API_VERSION_1_PREFIX)
    application_factory_logger.warning(
        MOCK_CUSTOMER_SIMULATOR_ACTIVE_WARNING, extra={"mock_customer_simulator": "enabled"}
    )


def create_application(
    settings: ApplicationSettings | None = None,
    id_generator: IdGenerator | None = None,
) -> FastAPI:
    """Builds the FastAPI application; its components are built at startup by the lifespan.

    The id generator, injectable for tests, makes correlation ids and every domain id. The
    labelled MockCustomerSimulator is mounted only when its setting is on, with a warning.
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
    if active_settings.mock_customer_simulator_enabled:
        mount_mock_customer_simulator(application)
    install_openapi_schema(application)
    return application
