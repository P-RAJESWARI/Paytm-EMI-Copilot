"""Writes backend/openapi.customer.json, the Phase 3A customer contract for the frontend client."""

from pathlib import Path

from openapi_spec_validator import validate

from emi_copilot.api.customer_contract_openapi_export import (
    build_customer_openapi_document,
    render_customer_openapi_document,
)

CUSTOMER_OPENAPI_DOCUMENT_PATH = Path(__file__).resolve().parents[1] / "openapi.customer.json"


def export_customer_openapi_document() -> None:
    """Validates the freshly built document, then writes it where the frontend reads it."""
    validate(build_customer_openapi_document())
    CUSTOMER_OPENAPI_DOCUMENT_PATH.write_text(render_customer_openapi_document(), encoding="utf-8")


if __name__ == "__main__":
    export_customer_openapi_document()
