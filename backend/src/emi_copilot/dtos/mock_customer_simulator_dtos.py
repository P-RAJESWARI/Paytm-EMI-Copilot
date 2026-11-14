"""Wire schema of the MockCustomerSimulator's agreed-plan call (not in openapi.json)."""

from typing import Annotated

from pydantic import Field

from emi_copilot.dtos.wire_types import CamelCaseRequestBodyModel, OpaqueIdentifier


class MockAgreedPlanRequest(CamelCaseRequestBodyModel):
    """The offer the simulated customer agrees to; every figure is re-quoted server-side."""

    offer_id: Annotated[OpaqueIdentifier, Field(examples=["mock-offer-no-cost-6m"])]
