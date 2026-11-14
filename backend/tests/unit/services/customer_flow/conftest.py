"""Wires the stub customer flow with the real Mock gateway, a fixed clock and a counting profile."""

from dataclasses import dataclass

import pytest

from emi_copilot.adapters.financial_profile.mock_adapter import MockSyntheticFinancialProfileAdapter
from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.domain.comfort import FinancialProfile
from emi_copilot.domain.money import Money
from emi_copilot.services.customer_flow.customer_flow_types import CustomerSessionCredentials
from emi_copilot.services.customer_flow.stub_customer_flow_services import (
    StubCustomerFlowServices,
    build_stub_customer_flow_services,
)
from emi_copilot.services.customer_flow.stub_design_sample import (
    STUB_RISKY_CUSTOMER_SESSION_ID,
    STUB_RISKY_QR_CODE,
    STUB_STANDARD_QR_CODE,
)
from tests.fakes.sequential_id_generator import SequentialIdGenerator
from tests.fixed_clock import FixedClock
from tests.payment_builders import CREATED_AT


class CountingFinancialProfilePort(FinancialProfilePort):
    """Delegates to the synthetic Mock and counts every read, to prove skipping reads nothing."""

    def __init__(self) -> None:
        """Wraps the Mock with the sample risky session listed."""
        self._mock_adapter = MockSyntheticFinancialProfileAdapter(
            frozenset({STUB_RISKY_CUSTOMER_SESSION_ID})
        )
        self.read_count = 0

    def get_financial_profile(self, customer_session_id: str) -> FinancialProfile:
        """Counts the read and gives the Mock's profile."""
        self.read_count += 1
        return self._mock_adapter.get_financial_profile(customer_session_id)


@dataclass
class CustomerFlowKit:
    """The stub services and the fakes they were built with."""

    services: StubCustomerFlowServices
    clock: FixedClock
    profile_port: CountingFinancialProfilePort

    def start_standard_session(self) -> CustomerSessionCredentials:
        """Scans the standard sample QR and gives the session's credentials."""
        return self._start(STUB_STANDARD_QR_CODE.qr_token)

    def start_risky_session(self) -> CustomerSessionCredentials:
        """Scans the risky sample QR and gives the session's credentials."""
        return self._start(STUB_RISKY_QR_CODE.qr_token)

    def confirm_budget(
        self, credentials: CustomerSessionCredentials, budget_in_rupees: str = "3000"
    ) -> None:
        """Confirms a monthly budget for the session."""
        self.services.session_service.confirm_budget(
            credentials, Money.from_rupees(budget_in_rupees)
        )

    def _start(self, qr_token: str) -> CustomerSessionCredentials:
        """Starts a session from a QR token."""
        started_session = self.services.session_service.start_session(qr_token)
        return CustomerSessionCredentials(
            started_session.customer_session_id, started_session.session_token
        )


@pytest.fixture
def kit() -> CustomerFlowKit:
    """Builds fresh stub services, so no test sees another's sessions."""
    clock = FixedClock(CREATED_AT)
    profile_port = CountingFinancialProfilePort()
    services = build_stub_customer_flow_services(
        MockPaymentGatewayAdapter(clock, bytes(range(32))),
        profile_port,
        clock,
        SequentialIdGenerator(),
    )
    return CustomerFlowKit(services=services, clock=clock, profile_port=profile_port)
