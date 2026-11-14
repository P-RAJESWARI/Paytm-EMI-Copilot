"""RFC 7807 problem details: the one error body every endpoint returns (api-conventions.md 4)."""

from typing import Annotated

from pydantic import Field

from emi_copilot.dtos.wire_types import CamelCaseResponseModel

PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"
PROBLEM_TYPE_BASE_URL = "https://emicopilot.example/problems/"


def build_problem_type_url(code: str) -> str:
    """Gives the problem type URL of a code: OFFER_NOT_FOUND becomes .../offer-not-found."""
    return PROBLEM_TYPE_BASE_URL + code.lower().replace("_", "-")


class FieldErrorResponse(CamelCaseResponseModel):
    """One invalid request field, named as on the wire, with an English message."""

    field: Annotated[str, Field(examples=["priceInPaise"])]
    message: Annotated[str, Field(examples=["Input should be greater than 0"])]


class ProblemDetailsResponse(CamelCaseResponseModel):
    """An error: a stable code for the UI to translate and an English detail for developers.

    It never holds a stack trace, SQL, a vendor payload or personal data.
    """

    type: Annotated[str, Field(examples=["https://emicopilot.example/problems/offer-not-found"])]
    title: Annotated[str, Field(examples=["Offer not found"])]
    status: Annotated[int, Field(ge=400, le=599, examples=[404])]
    detail: Annotated[
        str, Field(examples=["The chosen offer is not quoted for this item and price."])
    ]
    code: Annotated[str, Field(examples=["OFFER_NOT_FOUND"])]
    correlation_id: Annotated[str | None, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0B"])]
    field_errors: Annotated[
        list[FieldErrorResponse] | None,
        Field(description="Set only on request validation problems."),
    ] = None
