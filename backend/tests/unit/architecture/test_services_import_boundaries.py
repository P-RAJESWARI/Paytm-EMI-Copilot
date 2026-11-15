"""Services depend on the gateway ports, repositories, domain, events and six core modules only.

They never import a concrete adapter (the Mock, any Paytm module or the factory), a web
framework, the database library or the API layer (backend.md section 2, ADR 0008).
"""

import sys
from pathlib import Path

import pytest

from tests.unit.architecture.source_files import describe_source_file, list_services_modules
from tests.unit.architecture.test_import_boundaries import (
    is_inside_package,
    list_imported_module_names,
)

ALLOWED_APPLICATION_MODULES_IN_SERVICES = (
    "emi_copilot.adapters.payment_gateway.port",
    # The Mock's customer controls, a port too, used only by the labelled MockCustomerSimulator.
    "emi_copilot.adapters.payment_gateway.mock_payment_simulator_port",
    # The report ports (step 2.4): brand settlements and weekly message delivery.
    "emi_copilot.adapters.settlement.port",
    "emi_copilot.adapters.weekly_message_delivery.port",
    "emi_copilot.adapters.financial_profile.port",
    # The consent ports (ADR 0022): the customer's phone number, code delivery and code source.
    "emi_copilot.adapters.customer_contact.port",
    "emi_copilot.adapters.consent_otp.port",
    "emi_copilot.adapters.consent_otp.code_generator_port",
    # The AI ports and their typed values (Layer 4): requests, completions and prompt facts.
    "emi_copilot.adapters.ai.ai_types",
    "emi_copilot.adapters.ai.prompt_facts",
    "emi_copilot.adapters.ai.explanation_text_port",
    "emi_copilot.adapters.ai.speech_port",
    "emi_copilot.core.clock",
    "emi_copilot.core.id_generator",
    # Pure standard-library primitives: PIN hashing, opaque bearer tokens, customer QR tokens
    # and session codes.
    "emi_copilot.core.opaque_token",
    "emi_copilot.core.pin_hasher",
    "emi_copilot.core.qr_token_signer",
    "emi_copilot.core.session_code_generator",
    # Keyed hashes of the customer's phone and codes, and consent reference serials (ADR 0022).
    "emi_copilot.core.keyed_hasher",
    "emi_copilot.core.consent_reference_serial_generator",
    "emi_copilot.domain",
    "emi_copilot.events",
    "emi_copilot.repositories.unit_of_work_protocol",
    "emi_copilot.services",
)
CONCRETE_ADAPTER_WORDS = ("mock_adapter", "paytm", "factory")


def is_allowed_in_services(module_name: str) -> bool:
    """Tells whether a service may import the module: stdlib or an allowed application module."""
    top_level_package = module_name.split(".", maxsplit=1)[0]
    return top_level_package in sys.stdlib_module_names or any(
        is_inside_package(module_name, allowed_module)
        for allowed_module in ALLOWED_APPLICATION_MODULES_IN_SERVICES
    )


def find_imports_forbidden_in_services(source_file: Path) -> list[str]:
    """Lists the imports of a service module that are not allowed or name a concrete adapter."""
    return [
        module_name
        for module_name in list_imported_module_names(source_file)
        if not is_allowed_in_services(module_name)
        or any(word in module_name for word in CONCRETE_ADAPTER_WORDS)
    ]


def test_services_has_modules_to_check() -> None:
    """Guards the services boundary test against silently checking nothing."""
    assert len(list_services_modules()) >= 4


@pytest.mark.parametrize("services_module", list_services_modules(), ids=describe_source_file)
def test_services_module_imports_only_ports_repositories_domain_and_events(
    services_module: Path,
) -> None:
    """A service sees the gateway only through PaymentGatewayPort."""
    assert find_imports_forbidden_in_services(services_module) == []


def test_find_imports_forbidden_in_services_reports_adapters_frameworks_and_layers(
    tmp_path: Path,
) -> None:
    """The rule rejects the Mock, Paytm modules, the factory, FastAPI, SQLAlchemy and the API."""
    sample_module = tmp_path / "sample_module.py"
    sample_module.write_text(
        "import json\n"
        "from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort\n"
        "from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter\n"
        "from emi_copilot.adapters.payment_gateway.paytm_adapter import PaytmAdapter\n"
        "from emi_copilot.adapters.payment_gateway.factory import PaymentGatewayFactory\n"
        "from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork\n"
        "from emi_copilot.domain.payments import PaymentAttempt\n"
        "import fastapi\n"
        "import sqlalchemy\n"
        "from emi_copilot.api.controllers import health_controller\n",
        encoding="utf-8",
    )
    assert find_imports_forbidden_in_services(sample_module) == [
        "emi_copilot.adapters.payment_gateway.mock_adapter",
        "emi_copilot.adapters.payment_gateway.paytm_adapter",
        "emi_copilot.adapters.payment_gateway.factory",
        "emi_copilot.repositories.unit_of_work",
        "fastapi",
        "sqlalchemy",
        "emi_copilot.api.controllers",
    ]
