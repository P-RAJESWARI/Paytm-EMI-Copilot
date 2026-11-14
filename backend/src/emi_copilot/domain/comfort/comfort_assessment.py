"""ComfortAssessment: how one plan's monthly commitment sits beside the customer's existing EMIs."""

from dataclasses import dataclass

from emi_copilot.domain.comfort.comfort_band import ComfortBand
from emi_copilot.domain.comfort.comfort_band_classification_strategy import (
    ComfortBandClassificationStrategy,
)
from emi_copilot.domain.comfort.comfort_ratio import ComfortRatio
from emi_copilot.domain.comfort.financial_profile import FinancialProfile
from emi_copilot.domain.errors import InvalidComfortInputError
from emi_copilot.domain.money import Money


@dataclass(frozen=True, slots=True)
class ComfortAssessment:
    """The C5 figures for one plan: existing EMIs, this plan, both together, and the band.

    The band belongs to the total ratio. Each ratio is rounded on its own, so the two parts in basis
    points may differ from the total by one; the total is never the sum of rounded parts.
    """

    existing_emis_ratio: ComfortRatio
    plan_ratio: ComfortRatio
    total_ratio: ComfortRatio
    band: ComfortBand


def assess_comfort(
    profile: FinancialProfile,
    plan_monthly_commitment: Money,
    classification_strategy: ComfortBandClassificationStrategy,
) -> ComfortAssessment:
    """Works out the existing, plan and total ratios exactly and classifies the total."""
    if not isinstance(plan_monthly_commitment, Money):
        raise InvalidComfortInputError("The plan's monthly commitment must be Money.")
    monthly_inflow = profile.monthly_inflow
    total_ratio = ComfortRatio(
        profile.existing_emis_per_month + plan_monthly_commitment, monthly_inflow
    )
    return ComfortAssessment(
        existing_emis_ratio=ComfortRatio(profile.existing_emis_per_month, monthly_inflow),
        plan_ratio=ComfortRatio(plan_monthly_commitment, monthly_inflow),
        total_ratio=total_ratio,
        band=classification_strategy.classify(total_ratio),
    )
