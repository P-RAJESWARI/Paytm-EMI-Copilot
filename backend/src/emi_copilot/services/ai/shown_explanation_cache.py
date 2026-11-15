"""ShownExplanationCache: the explanations a customer session was shown, kept for a short while.

Asking again for the same plan gives the same text without another paid AI call, and speech
synthesis finds the shown text by its explanationId, so the voice says exactly what the screen
says (the client never supplies text to speak).
"""

from dataclasses import dataclass
from datetime import timedelta

from emi_copilot.core.bounded_timed_cache import BoundedTimedCache
from emi_copilot.core.clock import Clock
from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.sales import ChosenPlan
from emi_copilot.services.customer.explanation_types import ExplanationText

SHOWN_EXPLANATION_MAXIMUM_ENTRIES = 500
# As long as a customer session can last, so a shown text stays speakable for the whole visit.
SHOWN_EXPLANATION_LIFETIME = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class ShownExplanation:
    """One explanation as shown to one session: its opaque id, the plan figures and the text."""

    explanation_id: str
    customer_session_id: str
    plan: ChosenPlan
    explanation: ExplanationText


class ShownExplanationCache:
    """Finds a shown explanation by (session, offer, language) or by (session, explanationId)."""

    def __init__(
        self,
        clock: Clock,
        maximum_entries: int = SHOWN_EXPLANATION_MAXIMUM_ENTRIES,
        lifetime: timedelta = SHOWN_EXPLANATION_LIFETIME,
    ) -> None:
        """Builds the two bounded lookups on the injected clock."""
        self._by_plan: BoundedTimedCache[tuple[str, str, CustomerLanguage], ShownExplanation] = (
            BoundedTimedCache(clock, maximum_entries, lifetime)
        )
        self._by_explanation_id: BoundedTimedCache[tuple[str, str], ShownExplanation] = (
            BoundedTimedCache(clock, maximum_entries, lifetime)
        )

    def find_shown(
        self, customer_session_id: str, plan: ChosenPlan, language: CustomerLanguage
    ) -> ShownExplanation | None:
        """Gives the text shown for this plan, only while the plan's figures are unchanged."""
        shown = self._by_plan.find((customer_session_id, plan.offer_id, language))
        if shown is None or shown.plan != plan:
            return None
        return shown

    def find_by_explanation_id(
        self, customer_session_id: str, explanation_id: str
    ) -> ShownExplanation | None:
        """Gives the shown explanation with this id; another session's id finds nothing."""
        return self._by_explanation_id.find((customer_session_id, explanation_id))

    def remember(self, shown: ShownExplanation) -> None:
        """Keeps a newly shown explanation under both lookups."""
        session_id = shown.customer_session_id
        self._by_plan.store((session_id, shown.plan.offer_id, shown.explanation.language), shown)
        self._by_explanation_id.store((session_id, shown.explanation_id), shown)
