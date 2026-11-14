"""Wire schemas of PUT /api/v1/customer-sessions/{customerSessionId}/budget (C2)."""

from typing import Annotated, Literal

from pydantic import Field

from emi_copilot.domain.money import Money
from emi_copilot.dtos.wire_types import (
    CamelCaseRequestBodyModel,
    CamelCaseResponseModel,
    PositiveAmountInPaise,
)


class ConfirmBudgetRequest(CamelCaseRequestBodyModel):
    """The monthly amount the customer is comfortable paying, confirmed on screen by them.

    hasCustomerConfirmed must be true: a typed or spoken amount counts only once confirmed.
    """

    monthly_budget_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[300_000])]
    has_customer_confirmed: Annotated[Literal[True], Field(examples=[True])]

    def to_monthly_budget(self) -> Money:
        """Gives the budget as Money."""
        return Money.from_paise(self.monthly_budget_in_paise)


class ConfirmedBudgetResponse(CamelCaseResponseModel):
    """The monthly budget now held for the session."""

    monthly_budget_in_paise: Annotated[PositiveAmountInPaise, Field(examples=[300_000])]
    has_customer_confirmed: Annotated[bool, Field(examples=[True])]

    @classmethod
    def from_monthly_budget(cls, monthly_budget: Money) -> "ConfirmedBudgetResponse":
        """Converts the confirmed budget to integer paise."""
        return cls(monthly_budget_in_paise=monthly_budget.to_paise(), has_customer_confirmed=True)
