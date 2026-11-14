"""Wire schemas of the suggested actions: a stable code with typed paise parameters, no prose."""

from typing import Annotated, Literal

from pydantic import Field

from emi_copilot.domain.reports.suggested_actions import (
    CheaperModelAction,
    LongerNoCostPlanAction,
    SuggestedAction,
)
from emi_copilot.dtos.report_dtos import CustomerCount, to_paise_or_none
from emi_copilot.dtos.wire_types import CamelCaseResponseModel, PositiveAmountInPaise


class SuggestedNoCostTenureResponse(CamelCaseResponseModel):
    """A longer no-cost tenure and its regular monthly installment on the list price."""

    tenure_in_months: Annotated[int, Field(ge=1)]
    monthly_installment_in_paise: PositiveAmountInPaise


class LongerNoCostPlanParametersResponse(CamelCaseResponseModel):
    """Figures for "ask the brand for a longer no-cost plan" on the insight product."""

    product_id: str
    product_name: str
    current_no_cost_tenure_in_months: Annotated[int, Field(ge=1)]
    current_no_cost_monthly_in_paise: PositiveAmountInPaise
    suggested_tenures: list[SuggestedNoCostTenureResponse]
    missed_customer_count: CustomerCount
    is_missed_customer_count_suppressed: bool
    budget_ceiling_in_paise: PositiveAmountInPaise | None


class LongerNoCostPlanActionResponse(CamelCaseResponseModel):
    """ASK_BRAND_FOR_LONGER_NO_COST_PLAN with its parameters."""

    action_code: Literal["ASK_BRAND_FOR_LONGER_NO_COST_PLAN"]
    parameters: LongerNoCostPlanParametersResponse

    @classmethod
    def from_action(cls, action: LongerNoCostPlanAction) -> "LongerNoCostPlanActionResponse":
        """Builds the wire action."""
        return cls(
            action_code="ASK_BRAND_FOR_LONGER_NO_COST_PLAN",
            parameters=LongerNoCostPlanParametersResponse(
                product_id=action.product_id,
                product_name=action.product_name,
                current_no_cost_tenure_in_months=action.current_no_cost_tenure_in_months,
                current_no_cost_monthly_in_paise=action.current_no_cost_monthly.to_paise(),
                suggested_tenures=[
                    SuggestedNoCostTenureResponse(
                        tenure_in_months=tenure.tenure_in_months,
                        monthly_installment_in_paise=tenure.monthly_installment.to_paise(),
                    )
                    for tenure in action.suggested_tenures
                ],
                missed_customer_count=action.missed_count.customer_count,
                is_missed_customer_count_suppressed=action.missed_count.is_suppressed,
                budget_ceiling_in_paise=to_paise_or_none(action.budget_ceiling),
            ),
        )


class CheaperModelParametersResponse(CamelCaseResponseModel):
    """Figures for "keep the cheaper model ready": its price and no-extra-cost plan."""

    product_id: str
    product_name: str
    list_price_in_paise: PositiveAmountInPaise
    monthly_installment_in_paise: PositiveAmountInPaise
    tenure_in_months: Annotated[int, Field(ge=1)]


class CheaperModelActionResponse(CamelCaseResponseModel):
    """KEEP_CHEAPER_MODEL_READY with its parameters."""

    action_code: Literal["KEEP_CHEAPER_MODEL_READY"]
    parameters: CheaperModelParametersResponse

    @classmethod
    def from_action(cls, action: CheaperModelAction) -> "CheaperModelActionResponse":
        """Builds the wire action."""
        return cls(
            action_code="KEEP_CHEAPER_MODEL_READY",
            parameters=CheaperModelParametersResponse(
                product_id=action.product_id,
                product_name=action.product_name,
                list_price_in_paise=action.list_price.to_paise(),
                monthly_installment_in_paise=action.monthly_installment.to_paise(),
                tenure_in_months=action.tenure_in_months,
            ),
        )


SuggestedActionResponse = Annotated[
    LongerNoCostPlanActionResponse | CheaperModelActionResponse,
    Field(discriminator="action_code"),
]


class SuggestedActionsResponse(CamelCaseResponseModel):
    """M5 "What you can do to sell more", in a stable order; empty when nothing applies."""

    actions: list[SuggestedActionResponse]

    @classmethod
    def from_actions(cls, actions: tuple[SuggestedAction, ...]) -> "SuggestedActionsResponse":
        """Builds the wire list, one typed entry per action."""
        return cls(
            actions=[
                LongerNoCostPlanActionResponse.from_action(action)
                if isinstance(action, LongerNoCostPlanAction)
                else CheaperModelActionResponse.from_action(action)
                for action in actions
            ]
        )
