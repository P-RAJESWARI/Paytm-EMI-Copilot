"""SettlementPort contract, run against every implementation (only the labelled Mock today).

ADR 0006: no real settlement source exists yet; a real adapter joins the parametrisation with
recorded fixtures when one does.
"""

from collections.abc import Callable

import pytest

from emi_copilot.adapters.settlement.mock_adapter import MockSettlementAdapter
from emi_copilot.adapters.settlement.port import SettlementPort
from emi_copilot.domain.money import Money
from emi_copilot.domain.reports.money_due_report import MoneyDueReport
from emi_copilot.domain.settlements import BrandSettlementBatch

SETTLEMENT_ADAPTER_BUILDERS: dict[str, Callable[[], SettlementPort]] = {
    "mock": MockSettlementAdapter,
}


@pytest.fixture(params=sorted(SETTLEMENT_ADAPTER_BUILDERS))
def settlement_port(request: pytest.FixtureRequest) -> SettlementPort:
    """Builds each implementation in turn."""
    builder: Callable[[], SettlementPort] = SETTLEMENT_ADAPTER_BUILDERS[request.param]
    return builder()


def test_settlement_port_gives_numbered_whole_paise_batches_a_report_can_total(
    settlement_port: SettlementPort,
) -> None:
    """Every answer is a tuple of valid batches with distinct numbers, so MoneyDueReport works."""
    batches = settlement_port.find_expected_brand_settlements("RAVI-0193")
    assert isinstance(batches, tuple)
    assert all(isinstance(batch, BrandSettlementBatch) for batch in batches)
    MoneyDueReport.from_batches(batches)


def test_settlement_port_gives_an_unknown_shop_no_batches(settlement_port: SettlementPort) -> None:
    """A shop the source does not know has nothing due, never another shop's batches."""
    assert settlement_port.find_expected_brand_settlements("UNKNOWN-0000") == ()


def test_settlement_port_names_itself(settlement_port: SettlementPort) -> None:
    """The name is announced at startup."""
    assert settlement_port.adapter_name


def test_mock_settlement_gives_the_three_design_batches_for_the_demo_shop() -> None:
    """DESIGN_SPEC section 4: ₹72,000, ₹64,000 and ₹48,000, ₹1,84,000 in all."""
    report = MoneyDueReport.from_batches(
        MockSettlementAdapter().find_expected_brand_settlements("RAVI-0193")
    )
    assert report.total_due == Money.from_rupees("184000")
    assert [
        (batch.batch_number, batch.sale_count, batch.amount.to_paise(), batch.status.value)
        for batch in report.batches
    ] == [
        (1, 18, 7_200_000, "CLAIM_FILED"),
        (2, 16, 6_400_000, "WAITING_FOR_BRAND"),
        (3, 10, 4_800_000, "NOT_YET_DUE"),
    ]
    assert [batch.expected_date.isoformat() for batch in report.batches] == [
        "2027-01-13",
        "2027-01-28",
        "2027-02-12",
    ]
