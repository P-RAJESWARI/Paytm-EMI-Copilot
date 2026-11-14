"""Shared wire conventions: camelCase models, integer paise bounds and opaque identifiers."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

# JavaScript numbers are IEEE 754 doubles: above 2^53 - 1 (Number.MAX_SAFE_INTEGER) integers lose
# exactness, so a paise amount the browser parses could silently change. Every paise field on the
# wire is capped here, far above any real price (about ₹90 lakh crore).
MAXIMUM_SAFE_JAVASCRIPT_INTEGER = 9_007_199_254_740_991

PositiveAmountInPaise = Annotated[int, Field(gt=0, le=MAXIMUM_SAFE_JAVASCRIPT_INTEGER)]
"""An amount above zero, in integer paise."""

NonNegativeAmountInPaise = Annotated[int, Field(ge=0, le=MAXIMUM_SAFE_JAVASCRIPT_INTEGER)]
"""An amount of zero or more, in integer paise."""

# Visible ASCII without spaces: safe in logs and URLs, and never ambiguous about trailing blanks.
VISIBLE_ASCII_PATTERN = r"^[!-~]+$"
MAXIMUM_IDENTIFIER_LENGTH = 128

OpaqueIdentifier = Annotated[
    str,
    StringConstraints(
        min_length=1, max_length=MAXIMUM_IDENTIFIER_LENGTH, pattern=VISIBLE_ASCII_PATTERN
    ),
]
"""A catalogue, offer or order id we pass through without interpreting it."""


class CamelCaseQueryModel(BaseModel):
    """Base for query parameter models: camelCase names, unknown parameters refused.

    Query values always arrive as text, so numbers are parsed from it (lax mode).
    """

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True
    )


class CamelCaseRequestBodyModel(BaseModel):
    """Base for JSON request bodies: camelCase, unknown fields refused, no type coercion.

    Strict mode refuses "2200000" or 2200000.0 for a paise field, so money is a JSON integer.
    """

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", frozen=True, strict=True
    )


class CamelCaseResponseModel(BaseModel):
    """Base for response bodies: snake_case in Python, camelCase on the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, frozen=True)
