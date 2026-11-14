"""The Phase 3A customer contract application: customer routers only, wired to stub services.

This is a temporary composition root for the Phase 3A contract; it is merged into
api/dependencies.py in 3C, when the customer routers are mounted in main.py (ADR 0012). It
needs no database: the stub services keep sessions in memory and quote through the Mock gateway.
"""

import secrets

from fastapi import FastAPI

from emi_copilot.adapters.financial_profile.mock_adapter import MockSyntheticFinancialProfileAdapter
from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.adapters.payment_gateway.mock_adapter import (
    MINIMUM_WEBHOOK_SIGNING_SECRET_LENGTH_IN_BYTES,
    MockPaymentGatewayAdapter,
)
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.api.controllers.customer_routers import CUSTOMER_ROUTERS
from emi_copilot.api.error_handlers import register_error_handlers
from emi_copilot.api.openapi_documentation import install_openapi_schema
from emi_copilot.api.unexpected_error_middleware import UnexpectedErrorMiddleware
from emi_copilot.core.clock import Clock, SystemClock
from emi_copilot.core.id_generator import IdGenerator, UlidIdGenerator
from emi_copilot.core.request_context import CorrelationIdMiddleware
from emi_copilot.main import API_VERSION, API_VERSION_1_PREFIX
from emi_copilot.services.customer_flow.stub_customer_flow_services import (
    build_stub_customer_flow_services,
)
from emi_copilot.services.customer_flow.stub_design_sample import STUB_RISKY_CUSTOMER_SESSION_ID

CUSTOMER_CONTRACT_TITLE = "EMI-at-Counter Copilot customer API (Phase 3A contract)"


def build_customer_contract_application(
    clock: Clock | None = None,
    id_generator: IdGenerator | None = None,
    payment_gateway: PaymentGatewayPort | None = None,
    financial_profile_port: FinancialProfilePort | None = None,
) -> FastAPI:
    """Builds the contract application; every collaborator can be overridden by tests.

    Defaults: the system clock, ULIDs, the Mock gateway (built as the factory builds it in mock
    mode, with a fresh random webhook secret) and the synthetic profile Mock.
    """
    active_clock = clock or SystemClock()
    active_id_generator = id_generator or UlidIdGenerator()
    application = FastAPI(title=CUSTOMER_CONTRACT_TITLE, version=API_VERSION)
    # The same middleware order as main: the 500 handler runs inside the correlation id.
    application.add_middleware(UnexpectedErrorMiddleware)
    application.add_middleware(CorrelationIdMiddleware, id_generator=active_id_generator)
    register_error_handlers(application)
    for customer_router in CUSTOMER_ROUTERS:
        application.include_router(customer_router, prefix=API_VERSION_1_PREFIX)
    install_openapi_schema(application)
    application.state.customer_flow_services = build_stub_customer_flow_services(
        payment_gateway=payment_gateway
        or MockPaymentGatewayAdapter(
            active_clock, secrets.token_bytes(MINIMUM_WEBHOOK_SIGNING_SECRET_LENGTH_IN_BYTES)
        ),
        financial_profile_port=financial_profile_port
        or MockSyntheticFinancialProfileAdapter(frozenset({STUB_RISKY_CUSTOMER_SESSION_ID})),
        clock=active_clock,
        id_generator=active_id_generator,
    )
    return application
