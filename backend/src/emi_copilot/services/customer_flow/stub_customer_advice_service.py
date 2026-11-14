"""STUB until Phase 3C: the comfort check (C3), plan comparison (C4) and alternatives (C6)."""

from dataclasses import replace

from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.domain.comfort import FinancialProfile
from emi_copilot.domain.money import Money
from emi_copilot.services.customer_flow.customer_flow_types import (
    ComfortCheckOutcome,
    ComfortCheckStatus,
    CustomerSessionCredentials,
)
from emi_copilot.services.customer_flow.stub_customer_session_service import (
    StubCustomerSessionService,
    require_confirmed_budget,
)
from emi_copilot.services.customer_flow.stub_customer_session_store import (
    StubCustomerSessionStore,
)
from emi_copilot.services.customer_flow.stub_design_sample import (
    STUB_CHEAPER_MODEL,
    STUB_ITEM,
    STUB_PROFILES_ARE_SYNTHETIC,
)
from emi_copilot.services.plan_advice_service import PlanAdviceService
from emi_copilot.services.plan_advice_types import AlternativesAdvice, PlanComparison


class StubCustomerAdviceService:
    """STUB until Phase 3C: advice for the sample item; the profile is read only after consent.

    Without comfort check consent the FinancialProfilePort is never called, and plans show
    without bands. Every number comes from PlanAdviceService and the engines.
    """

    def __init__(
        self,
        store: StubCustomerSessionStore,
        session_service: StubCustomerSessionService,
        plan_advice_service: PlanAdviceService,
        financial_profile_port: FinancialProfilePort,
    ) -> None:
        """Keeps the store, the session checker, the advice use case and the profile port."""
        self._store = store
        self._session_service = session_service
        self._plan_advice_service = plan_advice_service
        self._financial_profile_port = financial_profile_port

    def run_comfort_check(
        self, credentials: CustomerSessionCredentials, has_customer_consented: bool
    ) -> ComfortCheckOutcome:
        """Records the C3 choice; with consent it reads the synthetic profile, else nothing."""
        with self._store.exclusive_access() as sessions:
            session = self._session_service.authenticate(sessions, credentials)
            require_confirmed_budget(session)
            sessions.save(replace(session, has_comfort_check_consent=has_customer_consented))
        if not has_customer_consented:
            return ComfortCheckOutcome(
                status=ComfortCheckStatus.SKIPPED,
                is_synthetic_data=STUB_PROFILES_ARE_SYNTHETIC,
                financial_profile=None,
            )
        return ComfortCheckOutcome(
            status=ComfortCheckStatus.COMPLETED,
            is_synthetic_data=STUB_PROFILES_ARE_SYNTHETIC,
            financial_profile=self._financial_profile_port.get_financial_profile(
                credentials.customer_session_id
            ),
        )

    def compare_plans(self, credentials: CustomerSessionCredentials) -> PlanComparison:
        """Ranks every plan for the confirmed budget, with comfort only after consent."""
        monthly_budget, financial_profile = self._read_budget_and_profile(credentials)
        return self._plan_advice_service.compare_plans(STUB_ITEM, monthly_budget, financial_profile)

    def suggest_alternatives(
        self, credentials: CustomerSessionCredentials, chosen_offer_id: str
    ) -> AlternativesAdvice:
        """Finds C6's alternatives to the chosen plan, offering the sample 64 GB model."""
        monthly_budget, financial_profile = self._read_budget_and_profile(credentials)
        return self._plan_advice_service.suggest_alternatives(
            STUB_ITEM, chosen_offer_id, monthly_budget, financial_profile, [STUB_CHEAPER_MODEL]
        )

    def _read_budget_and_profile(
        self, credentials: CustomerSessionCredentials
    ) -> tuple[Money, FinancialProfile | None]:
        """Gives the confirmed budget, and the profile only when the customer consented."""
        with self._store.exclusive_access() as sessions:
            session = self._session_service.authenticate(sessions, credentials)
            monthly_budget = require_confirmed_budget(session)
        if session.has_comfort_check_consent is not True:
            return monthly_budget, None
        return monthly_budget, self._financial_profile_port.get_financial_profile(
            credentials.customer_session_id
        )
