"""The customer flow routers, mounted under /api/v1 by main.py beside the merchant routers."""

from fastapi import APIRouter

from emi_copilot.api.controllers.comfort_check_controller import comfort_check_router
from emi_copilot.api.controllers.customer_budget_controller import customer_budget_router
from emi_copilot.api.controllers.customer_consent_controller import customer_consent_router
from emi_copilot.api.controllers.customer_explanation_controller import (
    customer_explanation_router,
)
from emi_copilot.api.controllers.customer_plan_controller import customer_plan_router
from emi_copilot.api.controllers.customer_receipt_controller import customer_receipt_router
from emi_copilot.api.controllers.customer_session_controller import customer_session_router
from emi_copilot.api.controllers.customer_speech_controller import customer_speech_router
from emi_copilot.api.controllers.customer_teach_back_controller import customer_teach_back_router

CUSTOMER_ROUTERS: tuple[APIRouter, ...] = (
    customer_session_router,
    customer_budget_router,
    comfort_check_router,
    customer_plan_router,
    customer_explanation_router,
    customer_speech_router,
    customer_teach_back_router,
    customer_consent_router,
    customer_receipt_router,
)
