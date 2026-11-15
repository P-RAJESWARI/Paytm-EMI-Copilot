"""Runs the real application on the test database with a chosen gateway and a fixed clock."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.api.dependencies import (
    build_rate_limiter,
    provide_clock,
    provide_payment_gateway,
    provide_unit_of_work_factory,
)
from emi_copilot.api.rate_limiting import (
    provide_ai_session_rate_limiter,
    provide_consent_otp_request_rate_limiter,
    provide_customer_consent_rate_limiter,
    provide_customer_session_start_rate_limiter,
    provide_merchant_payment_rate_limiter,
    provide_pairing_rate_limiter,
    provide_payment_webhook_rate_limiter,
)
from emi_copilot.config.ai_settings import AiProviderMode, AiSettings
from emi_copilot.config.settings import ApplicationSettings
from emi_copilot.core.fixed_window_rate_limiter import FixedWindowRateLimiter
from emi_copilot.domain.payments import AuditEvent, AuditEventType, PaymentAttempt
from emi_copilot.main import create_application
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock

SAMPLE_PRICE_IN_PAISE = 2_200_000
SAMPLE_ITEM_QUERY = {
    "priceInPaise": SAMPLE_PRICE_IN_PAISE,
    "productId": "product-tv-43",
    "brandId": "brand-demo",
    "categoryId": "category-televisions",
}


@dataclass
class ApiHarness:
    """The test client of the running application and readers of what it stored."""

    client: TestClient
    clock: FixedClock
    session_factory: sessionmaker[Session]

    def read_audit_events(self, event_type: AuditEventType) -> list[AuditEvent]:
        """Reads every committed audit event of one type, oldest first."""
        with SqlAlchemyUnitOfWork(self.session_factory, self.clock) as unit_of_work:
            return list(unit_of_work.audit_events.list_by_event_type(event_type))

    def count_all_audit_events(self) -> int:
        """Counts every committed audit event of every type."""
        return sum(len(self.read_audit_events(event_type)) for event_type in AuditEventType)

    def read_attempt(self, order_id: str) -> PaymentAttempt | None:
        """Reads the attempt stored for an order id, in a fresh transaction."""
        with SqlAlchemyUnitOfWork(self.session_factory, self.clock) as unit_of_work:
            return unit_of_work.payment_attempts.find_by_order_id(order_id)


def keep_limiter(limiter: FixedWindowRateLimiter) -> Callable[[], FixedWindowRateLimiter]:
    """Gives a provider override that always hands out the one test-clock limiter."""
    return lambda: limiter


@contextmanager
def open_api_harness(
    session_factory: sessionmaker[Session],
    clock: FixedClock,
    payment_gateway: PaymentGatewayPort,
    settings: ApplicationSettings | None = None,
) -> Iterator[ApiHarness]:
    """Starts the application, lifespan included, with gateway, database and clock overridden.

    The rate limiters are rebuilt on the test clock, so their windows move with the test. By
    default AI text is switched off, so Layer 2 and 3 tests pin the template text; the Layer 4
    tests pass settings with the labelled Mock text adapter instead. Speech stays the Mock.
    """
    # Built here, after the autouse fixture has hidden every AI variable of the environment.
    settings = settings or ApplicationSettings(
        ai_settings=AiSettings(explanation_text_provider_mode=AiProviderMode.OFF)
    )
    application = create_application(settings, id_generator=SequentialIdGenerator())
    application.dependency_overrides[provide_payment_gateway] = lambda: payment_gateway
    application.dependency_overrides[provide_unit_of_work_factory] = lambda: partial(
        SqlAlchemyUnitOfWork, session_factory, clock
    )
    application.dependency_overrides[provide_clock] = lambda: clock
    for limiter_provider, maximum_requests, window_in_seconds in (
        (
            provide_pairing_rate_limiter,
            settings.merchant_pairing_rate_limit_max_requests,
            settings.merchant_pairing_rate_limit_window_in_seconds,
        ),
        (
            provide_merchant_payment_rate_limiter,
            settings.merchant_payment_rate_limit_max_requests,
            settings.merchant_payment_rate_limit_window_in_seconds,
        ),
        (
            provide_payment_webhook_rate_limiter,
            settings.payment_webhook_rate_limit_max_requests,
            settings.payment_webhook_rate_limit_window_in_seconds,
        ),
        (
            provide_customer_session_start_rate_limiter,
            settings.customer_session_start_rate_limit_max_requests,
            settings.customer_session_start_rate_limit_window_in_seconds,
        ),
        (
            provide_consent_otp_request_rate_limiter,
            settings.consent_otp_request_rate_limit_max_requests,
            settings.consent_otp_request_rate_limit_window_in_seconds,
        ),
        (
            provide_customer_consent_rate_limiter,
            settings.customer_consent_rate_limit_max_requests,
            settings.customer_consent_rate_limit_window_in_seconds,
        ),
        (
            provide_ai_session_rate_limiter,
            settings.ai_settings.ai_session_rate_limit_max_requests,
            settings.ai_settings.ai_session_rate_limit_window_in_seconds,
        ),
    ):
        application.dependency_overrides[limiter_provider] = keep_limiter(
            build_rate_limiter(clock, maximum_requests, window_in_seconds)
        )
    with TestClient(application) as test_client:
        yield ApiHarness(client=test_client, clock=clock, session_factory=session_factory)
