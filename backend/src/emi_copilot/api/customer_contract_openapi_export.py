"""Renders the Phase 3A customer contract as `make openapi-customer` commits it.

The format matches openapi_export.py, so the frontend generator reads both the same way. The file
is backend/openapi.customer.json until Phase 3C merges the customer routes into openapi.json.
"""

import json
from typing import Any

from emi_copilot.api.customer_contract_application import build_customer_contract_application


def build_customer_openapi_document() -> dict[str, Any]:
    """Builds the customer contract's OpenAPI document; no startup or database is needed."""
    return build_customer_contract_application().openapi()


def render_customer_openapi_document() -> str:
    """Gives the document as stable, indented JSON with a final newline, ready to commit."""
    return json.dumps(build_customer_openapi_document(), indent=2, ensure_ascii=False) + "\n"
