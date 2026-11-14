"""The customer flow routers, mounted by the Phase 3A contract application only (ADR 0012)."""

from fastapi import APIRouter

from emi_copilot.api.controllers.comfort_check_controller import comfort_check_router
from emi_copilot.api.controllers.customer_budget_controller import customer_budget_router
from emi_copilot.api.controllers.customer_consent_controller import customer_consent_router
from emi_copilot.api.controllers.customer_plan_controller import customer_plan_router
from emi_copilot.api.controllers.customer_receipt_controller import customer_receipt_router
from emi_copilot.api.controllers.customer_session_controller import customer_session_router

# Phase 3C adds these to main.API_VERSION_1_ROUTERS; until then main never mounts them.
CUSTOMER_ROUTERS: tuple[APIRouter, ...] = (
    customer_session_router,
    customer_budget_router,
    comfort_check_router,
    customer_plan_router,
    customer_consent_router,
    customer_receipt_router,
)
