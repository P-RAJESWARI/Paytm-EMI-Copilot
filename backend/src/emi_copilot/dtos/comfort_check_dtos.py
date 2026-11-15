"""Wire schemas of the comfort check (C3) and the comfort figures shown beside each plan (C5)."""

from enum import StrEnum
from typing import Annotated

from pydantic import Field

from emi_copilot.domain.comfort import ComfortAssessment, ComfortBand
from emi_copilot.domain.customer_sessions import ComfortCheckStatus as StoredComfortCheckStatus
from emi_copilot.dtos.wire_types import (
    MAXIMUM_SAFE_JAVASCRIPT_INTEGER,
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    NonNegativeAmountInPaise,
    PositiveAmountInPaise,
)
from emi_copilot.services.customer.customer_session_types import ComfortCheckOutcome


class ComfortCheckStatus(StrEnum):
    """The customer's C3 answer on the wire; before any answer the field is null instead."""

    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"


def describe_comfort_check_answer(
    stored_status: StoredComfortCheckStatus,
) -> ComfortCheckStatus | None:
    """Gives the wire answer of a stored status: None until the customer has answered C3."""
    if stored_status is StoredComfortCheckStatus.NOT_ASKED:
        return None
    return ComfortCheckStatus(stored_status.value)


BasisPoints = Annotated[int, Field(ge=0, le=MAXIMUM_SAFE_JAVASCRIPT_INTEGER)]
"""A share as an integer in basis points: 3890 means 38.90% (api-conventions.md section 2)."""


class ComfortCheckRequest(CamelCaseRequestBodyModel):
    """The customer's C3 choice: allow the comfort check, or skip it (always allowed)."""

    has_customer_consented: Annotated[bool, Field(examples=[True])]


class ComfortCheckResponse(CamelCaseResponseModel):
    """The customer's own monthly figures read for the check; both are null when skipped.

    This is a customer endpoint: the merchant never sees these figures (CLAUDE.md section 2).
    """

    status: ComfortCheckStatus
    is_synthetic_data: Annotated[bool, Field(examples=[True])]
    monthly_inflow_in_paise: Annotated[PositiveAmountInPaise | None, Field(examples=[3_000_000])]
    existing_emis_in_paise: Annotated[NonNegativeAmountInPaise | None, Field(examples=[800_000])]

    @classmethod
    def from_outcome(cls, outcome: ComfortCheckOutcome) -> "ComfortCheckResponse":
        """Converts the outcome to integer paise; a skipped check carries no figures."""
        profile = outcome.financial_profile
        return cls(
            status=ComfortCheckStatus(outcome.status.value),
            is_synthetic_data=outcome.is_synthetic_data,
            monthly_inflow_in_paise=profile.monthly_inflow.to_paise() if profile else None,
            existing_emis_in_paise=profile.existing_emis_per_month.to_paise() if profile else None,
        )


class PlanComfortResponse(CamelCaseResponseModel):
    """One plan's band and shares of monthly inflow; advice, not a credit decision.

    comfortRatioInBasisPoints is (existing EMIs + this plan) / inflow, rounded half-up once, and
    the band is classified on it. The two shares are rounded on their own, so they may add up to
    one basis point more or less than the total (ADR 0020 decision 4).
    """

    band: ComfortBand
    comfort_ratio_in_basis_points: Annotated[BasisPoints, Field(examples=[3889])]
    plan_share_in_basis_points: Annotated[BasisPoints, Field(examples=[1222])]
    existing_emis_share_in_basis_points: Annotated[BasisPoints, Field(examples=[2667])]

    @classmethod
    def from_assessment(cls, assessment: ComfortAssessment | None) -> "PlanComfortResponse | None":
        """Converts an assessment to basis points; None when the comfort check was skipped."""
        if assessment is None:
            return None
        return cls(
            band=assessment.band,
            comfort_ratio_in_basis_points=assessment.total_ratio.in_basis_points,
            plan_share_in_basis_points=assessment.plan_ratio.in_basis_points,
            existing_emis_share_in_basis_points=assessment.existing_emis_ratio.in_basis_points,
        )
