"""CustomerContactPort contract, run against every implementation (only the labelled Mock today).

ADR 0022 decision 2: the real source is [Verify with Paytm]; a real adapter joins the
parametrisation with recorded fixtures when one exists.
"""

from collections.abc import Callable

import pytest

from emi_copilot.adapters.customer_contact.mock_adapter import MockPaytmCustomerContactAdapter
from emi_copilot.adapters.customer_contact.port import CustomerContactPort
from emi_copilot.domain.consent import CustomerPhoneNumber

CUSTOMER_CONTACT_ADAPTER_BUILDERS: dict[str, Callable[[], CustomerContactPort]] = {
    "mock": MockPaytmCustomerContactAdapter,
}


@pytest.fixture(params=sorted(CUSTOMER_CONTACT_ADAPTER_BUILDERS))
def customer_contact_port(request: pytest.FixtureRequest) -> CustomerContactPort:
    """Builds each implementation in turn."""
    builder: Callable[[], CustomerContactPort] = CUSTOMER_CONTACT_ADAPTER_BUILDERS[request.param]
    return builder()


def test_customer_contact_port_gives_a_validated_number_or_none(
    customer_contact_port: CustomerContactPort,
) -> None:
    """The answer is a CustomerPhoneNumber (ten digits, last two shown) or None, nothing else."""
    phone_number = customer_contact_port.find_customer_phone_number("01JCSALE000000000000000001")
    assert phone_number is None or isinstance(phone_number, CustomerPhoneNumber)
    if phone_number is not None:
        assert len(phone_number.national_number) == 10
        assert len(phone_number.last_two_digits) == 2


def test_customer_contact_port_answers_the_same_sale_the_same_way(
    customer_contact_port: CustomerContactPort,
) -> None:
    """Asking twice gives the same number, so a resent code goes to the same phone."""
    sale_id = "01JCSALE000000000000000001"
    assert customer_contact_port.find_customer_phone_number(sale_id) == (
        customer_contact_port.find_customer_phone_number(sale_id)
    )


def test_customer_contact_port_names_itself(customer_contact_port: CustomerContactPort) -> None:
    """The name is announced at startup."""
    assert customer_contact_port.adapter_name
