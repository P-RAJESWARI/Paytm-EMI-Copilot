"""CustomerTeachBackService: checks the customer's own words about a plan (C8); advisory only."""

from dataclasses import dataclass

from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.services.ai.teach_back_feedback import TeachBackFeedback
from emi_copilot.services.ai.teach_back_flow import TeachBackFlow
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.customer.explanation_types import (
    HighlightedAmount,
    highlight_plan_figures,
)
from emi_copilot.services.customer.session_plan_finder import SessionPlanFinder


@dataclass(frozen=True, slots=True)
class TeachBackOutcome:
    """The C8 card and the plan figures it restates, exactly as the engine computed them."""

    feedback: TeachBackFeedback
    highlighted_amounts: tuple[HighlightedAmount, ...]


class CustomerTeachBackService:
    """Scores the answer against one of the session's plans; nothing is stored or blocked.

    The answer never reaches an AI model: numbers are read deterministically (plan Q7).
    """

    def __init__(self, plan_finder: SessionPlanFinder, teach_back_flow: TeachBackFlow) -> None:
        """Keeps the plan lookup and the deterministic teach-back flow."""
        self._plan_finder = plan_finder
        self._teach_back_flow = teach_back_flow

    def check_for_session(
        self,
        credentials: CustomerSessionCredentials,
        offer_id: str,
        answer_text: str,
        language: CustomerLanguage,
    ) -> TeachBackOutcome:
        """Gives CLOSE_ENOUGH or TRY_AGAIN feedback; OfferNotFoundError for another item's plan."""
        plan = self._plan_finder.find_plan(credentials, offer_id)
        return TeachBackOutcome(
            feedback=self._teach_back_flow.check(plan, language, answer_text),
            highlighted_amounts=highlight_plan_figures(plan),
        )
