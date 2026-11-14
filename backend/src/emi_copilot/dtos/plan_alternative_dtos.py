"""Wire schemas of POST .../alternatives (C6): the chosen plan and its engine-recomputed options."""

from typing import Annotated

from pydantic import Field

from emi_copilot.domain.alternatives import AlternativeKind
from emi_copilot.domain.payments import EmiType
from emi_copilot.dtos.comfort_check_dtos import PlanComfortResponse
from emi_copilot.dtos.wire_types import (
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    NonNegativeAmountInPaise,
    OpaqueIdentifier,
    PositiveAmountInPaise,
)
from emi_copilot.services.plan_advice_types import AdvisedAlternative, AlternativesAdvice


class PlanAlternativesRequest(CamelCaseRequestBodyModel):
    """The plan the customer is looking at; alternatives are found for it."""

    offer_id: Annotated[OpaqueIdentifier, Field(examples=["mock-offer-no-cost-6m"])]


class BasePlanResponse(CamelCaseResponseModel):
    """The chosen plan ("Your plan" on C6) with its budget fit and comfort."""

    offer_id: Annotated[str, Field(examples=["mock-offer-no-cost-6m"])]
    lender_label: Annotated[str, Field(examples=["Brand"])]
    emi_type: EmiType
    tenure_in_months: Annotated[int, Field(ge=1, examples=[6])]
    monthly_installment_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[366_667])]
    last_installment_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[366_665])]
    extra_in_total_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[0])]
    total_payable_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    is_within_budget: Annotated[bool, Field(examples=[False])]
    amount_above_budget_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[66_667])]
    comfort: PlanComfortResponse | None

    @classmethod
    def from_advice(cls, advice: AlternativesAdvice) -> "BasePlanResponse":
        """Converts the chosen plan of the advice to integer paise and basis points."""
        priced_offer = advice.chosen_plan
        schedule = priced_offer.schedule
        return cls(
            offer_id=priced_offer.offer.offer_id,
            lender_label=priced_offer.offer.lender_label,
            emi_type=priced_offer.offer.emi_type,
            tenure_in_months=priced_offer.offer.tenure_in_months,
            monthly_installment_in_paise=priced_offer.quoted_monthly_installment.to_paise(),
            last_installment_in_paise=schedule.last_installment.to_paise(),
            extra_in_total_in_paise=schedule.extra_in_total.to_paise(),
            total_payable_in_paise=schedule.total_payable.to_paise(),
            price_in_paise=schedule.principal.to_paise(),
            is_within_budget=advice.chosen_plan_budget_fit.is_within_budget,
            amount_above_budget_in_paise=(
                advice.chosen_plan_budget_fit.amount_above_budget.to_paise()
            ),
            comfort=PlanComfortResponse.from_assessment(advice.chosen_plan_comfort),
        )


class PlanAlternativeResponse(CamelCaseResponseModel):
    """One option: down payment, longer tenure or cheaper model, kept even if it costs more.

    financedAmountInPaise is what the plan spreads over its months: the price less any down
    payment. The two monthly figures are the lender's quoted ones; isLowerMonthlyAmount and the
    budget fit compare the largest single installments (ADR 0020 decision 3).
    """

    kind: AlternativeKind
    offer_id: Annotated[str, Field(examples=["mock-offer-no-cost-6m"])]
    tenure_in_months: Annotated[int, Field(ge=1, examples=[6])]
    down_payment_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[400_000])]
    financed_amount_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[1_800_000])]
    product_id: Annotated[str | None, Field(examples=[None])]
    product_name: Annotated[str | None, Field(examples=[None])]
    price_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[2_200_000])]
    monthly_installment_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[300_000])]
    previous_monthly_installment_in_paise: Annotated[
        PositiveAmountInPaise, Field(examples=[366_667])
    ]
    extra_in_total_in_paise: Annotated[NonNegativeAmountInPaise, Field(examples=[0])]
    total_payable_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[1_800_000])]
    is_lower_monthly_amount: Annotated[bool, Field(examples=[True])]
    is_within_budget: Annotated[bool, Field(examples=[True])]
    comfort: PlanComfortResponse | None

    @classmethod
    def from_advised_alternative(
        cls, advised_alternative: AdvisedAlternative, previous_monthly_installment_in_paise: int
    ) -> "PlanAlternativeResponse":
        """Converts one alternative to integer paise and basis points."""
        alternative = advised_alternative.alternative
        priced_offer = alternative.priced_offer
        schedule = priced_offer.schedule
        return cls(
            kind=alternative.kind,
            offer_id=priced_offer.offer.offer_id,
            tenure_in_months=priced_offer.offer.tenure_in_months,
            down_payment_in_paise=alternative.down_payment.to_paise(),
            financed_amount_in_paise=schedule.principal.to_paise(),
            product_id=alternative.product_id,
            product_name=alternative.product_name,
            price_in_paise=(schedule.principal + alternative.down_payment).to_paise(),
            monthly_installment_in_paise=priced_offer.quoted_monthly_installment.to_paise(),
            previous_monthly_installment_in_paise=previous_monthly_installment_in_paise,
            extra_in_total_in_paise=schedule.extra_in_total.to_paise(),
            total_payable_in_paise=schedule.total_payable.to_paise(),
            is_lower_monthly_amount=alternative.is_lower_monthly_amount,
            is_within_budget=alternative.budget_fit.is_within_budget,
            comfort=PlanComfortResponse.from_assessment(advised_alternative.comfort),
        )


class PlanAlternativesResponse(CamelCaseResponseModel):
    """The chosen plan and every option; hasLowerMonthlyAlternative false is "nothing better"."""

    base_plan: BasePlanResponse
    has_lower_monthly_alternative: Annotated[bool, Field(examples=[True])]
    alternatives: list[PlanAlternativeResponse]

    @classmethod
    def from_advice(cls, advice: AlternativesAdvice) -> "PlanAlternativesResponse":
        """Converts the advice, keeping the C6 order of the alternatives."""
        previous_monthly_installment_in_paise = (
            advice.chosen_plan.quoted_monthly_installment.to_paise()
        )
        return cls(
            base_plan=BasePlanResponse.from_advice(advice),
            has_lower_monthly_alternative=advice.has_lower_monthly_alternative,
            alternatives=[
                PlanAlternativeResponse.from_advised_alternative(
                    advised_alternative, previous_monthly_installment_in_paise
                )
                for advised_alternative in advice.advised_alternatives
            ],
        )
