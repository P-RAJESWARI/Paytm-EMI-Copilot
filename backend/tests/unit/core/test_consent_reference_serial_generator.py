"""RandomConsentReferenceSerialGenerator draws four-digit serials from the system source."""

import pytest

from emi_copilot.core import consent_reference_serial_generator
from emi_copilot.core.consent_reference_serial_generator import (
    RandomConsentReferenceSerialGenerator,
)


def test_random_serial_numbers_are_from_0_to_9999() -> None:
    """Every serial fits the NNNN part of EMI-DDMM-NNNN."""
    generator = RandomConsentReferenceSerialGenerator()
    assert all(0 <= generator.new_serial_number() <= 9999 for _ in range(200))


def test_random_serial_numbers_come_from_the_secrets_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The system source is asked for a number below 10,000."""
    requested_bounds: list[int] = []

    def fake_randbelow(exclusive_upper_bound: int) -> int:
        """Records the bound and answers 42."""
        requested_bounds.append(exclusive_upper_bound)
        return 42

    monkeypatch.setattr(
        f"{consent_reference_serial_generator.__name__}.secrets.randbelow", fake_randbelow
    )
    assert RandomConsentReferenceSerialGenerator().new_serial_number() == 42
    assert requested_bounds == [10_000]
