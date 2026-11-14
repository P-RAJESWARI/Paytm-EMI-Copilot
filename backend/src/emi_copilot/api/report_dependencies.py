"""Providers of the report services, assembled per request from the startup components.

Kept beside dependencies.py (the composition root) so neither file outgrows its size limit;
the settlement and delivery adapters themselves are built only there, by their factories.
"""

from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends

from emi_copilot.adapters.settlement.port import SettlementPort
from emi_copilot.adapters.weekly_message_delivery.port import WeeklyMessageDeliveryPort
from emi_copilot.api.dependencies import (
    ClockDependency,
    ComponentsDependency,
    IdGeneratorDependency,
    OfferDiscoveryServiceDependency,
    UnitOfWorkFactoryDependency,
)
from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.domain.reports.small_count_suppression import SmallCountSuppressionPolicy
from emi_copilot.domain.reports.weekly_message_template import WeeklyMessageTemplate
from emi_copilot.services.missed_sales_analyser import MissedSalesAnalyser
from emi_copilot.services.report_periods import ReportPeriods
from emi_copilot.services.report_services import (
    FunnelReportService,
    MissedSalesReportService,
    MoneyDueReportService,
    SuggestedActionsService,
)
from emi_copilot.services.weekly_message_service import (
    WeeklyMessageReports,
    WeeklyMessageService,
)

SUPPRESSION_POLICY = SmallCountSuppressionPolicy()
"""The one count policy every report uses (threshold 5, plan Q3); it holds no mutable state."""


def provide_settlement(components: ComponentsDependency) -> SettlementPort:
    """Gives the settlement port built at startup (the labelled Mock)."""
    return components.settlement


def provide_weekly_message_delivery(components: ComponentsDependency) -> WeeklyMessageDeliveryPort:
    """Gives the weekly message delivery port built at startup (the labelled Mock)."""
    return components.weekly_message_delivery


def provide_report_periods(
    components: ComponentsDependency, clock: ClockDependency
) -> ReportPeriods:
    """Builds the period calculator on the request's clock in the reporting time zone."""
    return ReportPeriods(clock, ZoneInfo(components.settings.reporting_time_zone))


SettlementDependency = Annotated[SettlementPort, Depends(provide_settlement)]
WeeklyMessageDeliveryDependency = Annotated[
    WeeklyMessageDeliveryPort, Depends(provide_weekly_message_delivery)
]
ReportPeriodsDependency = Annotated[ReportPeriods, Depends(provide_report_periods)]


def provide_missed_sales_analyser(
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    offer_discovery_service: OfferDiscoveryServiceDependency,
) -> MissedSalesAnalyser:
    """Assembles the analyser on offer discovery."""
    return MissedSalesAnalyser(unit_of_work_factory, offer_discovery_service)


MissedSalesAnalyserDependency = Annotated[
    MissedSalesAnalyser, Depends(provide_missed_sales_analyser)
]


def provide_funnel_report_service(
    unit_of_work_factory: UnitOfWorkFactoryDependency, report_periods: ReportPeriodsDependency
) -> FunnelReportService:
    """Assembles the funnel report service."""
    return FunnelReportService(unit_of_work_factory, report_periods, SUPPRESSION_POLICY)


def provide_missed_sales_report_service(
    analyser: MissedSalesAnalyserDependency, report_periods: ReportPeriodsDependency
) -> MissedSalesReportService:
    """Assembles the missed-sales report service."""
    return MissedSalesReportService(analyser, report_periods, SUPPRESSION_POLICY)


def provide_suggested_actions_service(
    analyser: MissedSalesAnalyserDependency, report_periods: ReportPeriodsDependency
) -> SuggestedActionsService:
    """Assembles the suggested-actions service."""
    return SuggestedActionsService(analyser, report_periods, SUPPRESSION_POLICY)


def provide_money_due_report_service(settlement: SettlementDependency) -> MoneyDueReportService:
    """Assembles the money-due service on the settlement port."""
    return MoneyDueReportService(settlement)


FunnelReportServiceDependency = Annotated[
    FunnelReportService, Depends(provide_funnel_report_service)
]
MissedSalesReportServiceDependency = Annotated[
    MissedSalesReportService, Depends(provide_missed_sales_report_service)
]
SuggestedActionsServiceDependency = Annotated[
    SuggestedActionsService, Depends(provide_suggested_actions_service)
]
MoneyDueReportServiceDependency = Annotated[
    MoneyDueReportService, Depends(provide_money_due_report_service)
]


def provide_weekly_message_service(  # noqa: PLR0913 - one parameter per injected component
    *,
    unit_of_work_factory: UnitOfWorkFactoryDependency,
    clock: ClockDependency,
    id_generator: IdGeneratorDependency,
    report_periods: ReportPeriodsDependency,
    funnel: FunnelReportServiceDependency,
    missed_sales: MissedSalesReportServiceDependency,
    suggested_actions: SuggestedActionsServiceDependency,
    money_due: MoneyDueReportServiceDependency,
    delivery: WeeklyMessageDeliveryDependency,
) -> WeeklyMessageService:
    """Assembles the weekly message service with the one money formatter (plan Q14)."""
    return WeeklyMessageService(
        unit_of_work_factory=unit_of_work_factory,
        clock=clock,
        id_generator=id_generator,
        report_periods=report_periods,
        reports=WeeklyMessageReports(funnel, missed_sales, suggested_actions, money_due),
        template=WeeklyMessageTemplate(format_paise_as_whole_rupees),
        delivery=delivery,
    )


WeeklyMessageServiceDependency = Annotated[
    WeeklyMessageService, Depends(provide_weekly_message_service)
]
