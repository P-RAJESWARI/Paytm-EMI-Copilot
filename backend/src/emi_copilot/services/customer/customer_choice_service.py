"""CustomerChoiceService: the customer's own answers: language (C1), budget (C2), comfort (C3)."""

from emi_copilot.adapters.financial_profile.port import FinancialProfilePort
from emi_copilot.core.clock import Clock
from emi_copilot.domain.customer_sessions import ComfortCheckStatus, CustomerLanguage
from emi_copilot.domain.errors import DomainError
from emi_copilot.domain.events import CustomerBudgetConfirmed
from emi_copilot.domain.money import Money
from emi_copilot.domain.ranking import require_valid_monthly_budget
from emi_copilot.events.event_bus import DomainEventBus
from emi_copilot.repositories.unit_of_work_protocol import UnitOfWorkFactory
from emi_copilot.services.customer.customer_session_access import (
    CustomerSessionAccess,
    require_confirmed_budget,
)
from emi_copilot.services.customer.customer_session_types import (
    ComfortCheckOutcome,
    CustomerSessionCredentials,
)
from emi_copilot.services.sale_expiry import SaleExpiryStep


class CustomerChoiceService:
    """Records what the customer chose on their phone; the merchant never sees any of it.

    Budget and comfort answers are taken only while the sale is CHOOSING. The comfort check
    stores the choice only: income and existing EMIs are read from FinancialProfilePort when
    shown, never stored (security-and-compliance.md section 2).
    """

    def __init__(  # noqa: PLR0913 - a use case wired with its collaborators, by keyword
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        clock: Clock,
        event_bus: DomainEventBus,
        sale_expiry: SaleExpiryStep,
        financial_profile_port: FinancialProfilePort,
        are_financial_profiles_synthetic: bool,
    ) -> None:
        """Keeps the collaborators and whether the profile port gives synthetic (Mock) data."""
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._event_bus = event_bus
        self._session_access = CustomerSessionAccess(sale_expiry)
        self._financial_profile_port = financial_profile_port
        self._are_financial_profiles_synthetic = are_financial_profiles_synthetic

    def choose_language(
        self, credentials: CustomerSessionCredentials, language: CustomerLanguage
    ) -> CustomerLanguage:
        """Records the language chosen on C1, which later screens and the receipt use."""
        with self._unit_of_work_factory() as unit_of_work:
            session = self._session_access.authenticate(
                unit_of_work, credentials, self._clock.now()
            )
            unit_of_work.customer_sessions.update(session.choose_language(language))
        return language

    def confirm_budget(
        self, credentials: CustomerSessionCredentials, monthly_budget: Money
    ) -> Money:
        """Stores the budget the customer confirmed on C2 and announces it for the funnel.

        Every confirmation is announced; the funnel keeps only the sale's first budget.
        """
        require_valid_monthly_budget(monthly_budget)
        refusal: DomainError | None = None
        with self._unit_of_work_factory() as unit_of_work:
            now = self._clock.now()
            opened = self._session_access.open_sale(unit_of_work, credentials, now)
            refusal = opened.find_choosing_refusal()
            if refusal is None:
                unit_of_work.customer_sessions.update(opened.session.confirm_budget(monthly_budget))
                self._event_bus.publish(
                    CustomerBudgetConfirmed(
                        occurred_at=now,
                        sale_id=opened.sale.id,
                        merchant_id=opened.sale.merchant_id,
                        monthly_budget_in_paise=monthly_budget.to_paise(),
                    ),
                    unit_of_work,
                )
        if refusal is not None:
            raise refusal
        return monthly_budget

    def record_comfort_check_choice(
        self, credentials: CustomerSessionCredentials, *, has_customer_consented: bool
    ) -> ComfortCheckOutcome:
        """Records C3's Allow or Skip; with consent it reads the profile to show it, else nothing.

        The profile port is called only after the customer allowed it (CLAUDE.md rule 9).
        """
        refusal: DomainError | None = None
        with self._unit_of_work_factory() as unit_of_work:
            opened = self._session_access.open_sale(unit_of_work, credentials, self._clock.now())
            refusal = opened.find_choosing_refusal()
            if refusal is None:
                require_confirmed_budget(opened.session)
                unit_of_work.customer_sessions.update(
                    opened.session.record_comfort_check_choice(has_consented=has_customer_consented)
                )
        if refusal is not None:
            raise refusal
        if not has_customer_consented:
            return ComfortCheckOutcome(
                status=ComfortCheckStatus.SKIPPED,
                is_synthetic_data=self._are_financial_profiles_synthetic,
                financial_profile=None,
            )
        return ComfortCheckOutcome(
            status=ComfortCheckStatus.COMPLETED,
            is_synthetic_data=self._are_financial_profiles_synthetic,
            financial_profile=self._financial_profile_port.get_financial_profile(
                credentials.customer_session_id
            ),
        )
