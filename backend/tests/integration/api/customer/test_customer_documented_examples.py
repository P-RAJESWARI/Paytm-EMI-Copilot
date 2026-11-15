"""The OpenAPI examples are what the real services answer on the design data (no drift)."""

from typing import Any

import pytest

from emi_copilot.api.controllers.customer_response_examples import (
    BUDGET_RESPONSE_EXAMPLE,
    COMFORT_CHECK_RESPONSE_EXAMPLE,
    CONSENT_RESPONSE_EXAMPLE,
    CUSTOMER_SESSION_RESPONSE_EXAMPLE,
    CUSTOMER_SESSION_SUMMARY_RESPONSE_EXAMPLE,
    EXAMPLE_PHONE_64_GB_PRODUCT_ID,
    EXAMPLE_PHONE_128_GB_PRODUCT_ID,
    OTP_CHALLENGE_RESPONSE_EXAMPLE,
    PLAN_ALTERNATIVES_RESPONSE_EXAMPLE,
    PLAN_EXPLANATION_RESPONSE_EXAMPLE,
    PLANS_RESPONSE_EXAMPLE,
    RECEIPT_RESPONSE_EXAMPLE,
)
from tests.integration.api.customer.customer_api_helpers import (
    PHONE_64_GB_ID,
    PHONE_128_GB_ID,
    CustomerFlowHarness,
)

pytestmark = pytest.mark.integration

RANDOM_FIELD_NAMES = ("customerSessionId", "sessionToken", "sessionCode", "consentId")
"""Ids, tokens and the random session code; every other documented value must match exactly."""
EXAMPLE_PRODUCT_IDS = {
    PHONE_128_GB_ID: EXAMPLE_PHONE_128_GB_PRODUCT_ID,
    PHONE_64_GB_ID: EXAMPLE_PHONE_64_GB_PRODUCT_ID,
}


def mask_random_fields(node: object) -> object:
    """Replaces the random fields with a marker and the stored product ids with the examples'."""
    if isinstance(node, dict):
        return {
            key: "<random>" if key in RANDOM_FIELD_NAMES else mask_random_fields(value)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [mask_random_fields(item) for item in node]
    if isinstance(node, str):
        return EXAMPLE_PRODUCT_IDS.get(node, node)
    return node


def assert_documented(actual_body: dict[str, Any], documented_body: dict[str, Any]) -> None:
    """Requires the answer to equal its documented example, random fields aside."""
    assert mask_random_fields(actual_body) == mask_random_fields(documented_body)


def test_design_flow_answers_exactly_the_documented_examples(
    customer_flow: CustomerFlowHarness,
) -> None:
    """Session, budget, comfort, plans, alternatives, explanation, code, consent, receipt."""
    session = customer_flow.open_customer_session()
    assert_documented(session.started_body, CUSTOMER_SESSION_RESPONSE_EXAMPLE)
    assert_documented(session.confirm_budget().json(), BUDGET_RESPONSE_EXAMPLE)
    assert_documented(
        session.answer_comfort_check(has_customer_consented=True).json(),
        COMFORT_CHECK_RESPONSE_EXAMPLE,
    )
    assert_documented(session.get_plans().json(), PLANS_RESPONSE_EXAMPLE)
    assert_documented(session.find_alternatives().json(), PLAN_ALTERNATIVES_RESPONSE_EXAMPLE)
    assert_documented(
        session.explain(accept_language="en").json(), PLAN_EXPLANATION_RESPONSE_EXAMPLE
    )
    assert_documented(session.request_code().json(), OTP_CHALLENGE_RESPONSE_EXAMPLE)
    consent_response = session.give_consent()
    assert consent_response.status_code == 201, consent_response.text
    assert_documented(consent_response.json(), CONSENT_RESPONSE_EXAMPLE)
    assert_documented(session.get_receipt().json(), RECEIPT_RESPONSE_EXAMPLE)
    assert_documented(session.get_summary().json(), CUSTOMER_SESSION_SUMMARY_RESPONSE_EXAMPLE)
