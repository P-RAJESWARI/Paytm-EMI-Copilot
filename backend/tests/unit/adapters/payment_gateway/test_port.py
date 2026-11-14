"""Tests that pin the shape of PaymentGatewayPort, the contract every gateway adapter fulfils."""

import inspect

import pytest

from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort


def test_payment_gateway_port_declares_exactly_the_domain_operations() -> None:
    """The port offers the four gateway operations in our words plus the adapter name."""
    assert PaymentGatewayPort.__abstractmethods__ == frozenset(
        {
            "adapter_name",
            "discover_offers",
            "create_payment_link",
            "get_payment_status",
            "verify_webhook",
        }
    )


def test_payment_gateway_port_cannot_be_instantiated_without_an_adapter() -> None:
    """Only a concrete adapter that implements every operation can serve as the gateway."""
    with pytest.raises(TypeError, match="abstract"):
        PaymentGatewayPort()  # type: ignore[abstract]


def test_payment_gateway_port_adapter_name_is_a_read_only_property() -> None:
    """The adapter name is read, never assigned, so the announced mode cannot drift."""
    adapter_name_attribute = inspect.getattr_static(PaymentGatewayPort, "adapter_name")
    assert isinstance(adapter_name_attribute, property)
    assert adapter_name_attribute.fset is None
