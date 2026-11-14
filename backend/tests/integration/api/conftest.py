"""API integration fixtures: the application on the test database, Mock or fake gateway."""

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from tests.fakes.fake_payment_gateway import FakePaymentGateway
from tests.fixed_clock import FixedClock
from tests.integration.api.api_harness import ApiHarness, open_api_harness
from tests.integration.api.sale_api_helpers import TwoShops, store_and_pair_two_shops

MOCK_WEBHOOK_SIGNING_SECRET = b"api-integration-test-mock-signing-key"


@pytest.fixture
def mock_gateway(fixed_clock: FixedClock) -> MockPaymentGatewayAdapter:
    """Builds the Mock gateway on the test clock, so its payment delay is under test control."""
    return MockPaymentGatewayAdapter(fixed_clock, MOCK_WEBHOOK_SIGNING_SECRET)


@pytest.fixture
def mock_api(
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
    mock_gateway: MockPaymentGatewayAdapter,
) -> Iterator[ApiHarness]:
    """Runs the application with the Mock gateway, the default adapter."""
    with open_api_harness(session_factory, fixed_clock, mock_gateway) as harness:
        yield harness


@pytest.fixture
def fake_gateway() -> FakePaymentGateway:
    """Builds a scripted gateway that records every call."""
    return FakePaymentGateway()


@pytest.fixture
def fake_api(
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
    fake_gateway: FakePaymentGateway,
) -> Iterator[ApiHarness]:
    """Runs the application with the scripted fake gateway."""
    with open_api_harness(session_factory, fixed_clock, fake_gateway) as harness:
        yield harness


@pytest.fixture
def shops(mock_api: ApiHarness) -> TwoShops:
    """Two paired shops, each with the three M2 products, on the Mock gateway application."""
    return store_and_pair_two_shops(mock_api)
