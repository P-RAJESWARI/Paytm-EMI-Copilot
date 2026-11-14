"""Runs every payment gateway contract test once per gateway implementation harness."""

from collections.abc import Callable

import pytest

from tests.contract.payment_gateway.gateway_contract_harness import GatewayContractHarness
from tests.contract.payment_gateway.mock_gateway_contract_harness import (
    MockGatewayContractHarness,
)

# One entry per gateway implementation; the real adapter's fixture-fed harness joins here.
GATEWAY_CONTRACT_HARNESS_FACTORIES: dict[str, Callable[[], GatewayContractHarness]] = {
    "mock": MockGatewayContractHarness,
}


@pytest.fixture(params=sorted(GATEWAY_CONTRACT_HARNESS_FACTORIES))
def gateway_contract_harness(request: pytest.FixtureRequest) -> GatewayContractHarness:
    """Gives a fresh harness for each implementation, so no test sees another's state."""
    harness_name: str = request.param
    return GATEWAY_CONTRACT_HARNESS_FACTORIES[harness_name]()
