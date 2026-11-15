"""Customer API fixtures: the design moment, the design shop and a fixed reference serial."""

import pytest

from emi_copilot.api.customer_dependencies import provide_consent_reference_serial_generator
from tests.fakes.fake_customer_flow_ports import FixedConsentReferenceSerialGenerator
from tests.fixed_clock import FixedClock
from tests.integration.api.api_harness import ApiHarness
from tests.integration.api.customer.customer_api_helpers import (
    DESIGN_MOMENT,
    CustomerFlowHarness,
    store_ravi_electronics,
)


@pytest.fixture
def fixed_clock() -> FixedClock:
    """Starts every customer test at the documented examples' moment, 2026-11-15T09:30:00Z."""
    return FixedClock(DESIGN_MOMENT)


@pytest.fixture
def customer_flow(mock_api: ApiHarness) -> CustomerFlowHarness:
    """Pairs Ravi Electronics on the Mock gateway application; references use serial 42."""
    merchant_headers = store_ravi_electronics(mock_api)
    mock_api.client.app.dependency_overrides[provide_consent_reference_serial_generator] = (  # type: ignore[attr-defined]
        FixedConsentReferenceSerialGenerator
    )
    return CustomerFlowHarness(api=mock_api, merchant_headers=merchant_headers)
