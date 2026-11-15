"""CustomerExplanationService: explains one of the session's plans with fresh figures (C7)."""

from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.services.ai.shown_explanation_cache import ShownExplanation, ShownExplanationCache
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from emi_copilot.services.customer.explanation_types import PlanExplainer
from emi_copilot.services.customer.session_plan_finder import SessionPlanFinder


class CustomerExplanationService:
    """Re-quotes the chosen offer on the session's item and hands its figures to the explainer.

    The explainer is the AuditedExplanationService (AI text checked by the number audit, the
    template otherwise) behind the PlanExplainer interface. It only words the figures; it never
    computes or changes them (CLAUDE.md section 2, rules 1 and 2). A shown text is remembered,
    so asking again gives the same text and the same explanationId without another AI call.
    """

    def __init__(
        self,
        plan_finder: SessionPlanFinder,
        plan_explainer: PlanExplainer,
        shown_explanation_cache: ShownExplanationCache,
        id_generator: IdGenerator,
    ) -> None:
        """Keeps the plan lookup, the explainer, the shown-text cache and the id source."""
        self._plan_finder = plan_finder
        self._plan_explainer = plan_explainer
        self._shown_explanation_cache = shown_explanation_cache
        self._id_generator = id_generator

    def explain_for_session(
        self, credentials: CustomerSessionCredentials, offer_id: str, language: CustomerLanguage
    ) -> ShownExplanation:
        """Explains the offer as quoted now for the session's item at the sale price.

        Raises OfferNotFoundError when the offer is not quoted for that item and price.
        """
        plan = self._plan_finder.find_plan(credentials, offer_id)
        session_id = credentials.customer_session_id
        already_shown = self._shown_explanation_cache.find_shown(session_id, plan, language)
        if already_shown is not None:
            return already_shown
        shown = ShownExplanation(
            explanation_id=self._id_generator.new_id(),
            customer_session_id=session_id,
            plan=plan,
            explanation=self._plan_explainer.explain(
                plan, language, customer_session_id=session_id
            ),
        )
        self._shown_explanation_cache.remember(shown)
        return shown
