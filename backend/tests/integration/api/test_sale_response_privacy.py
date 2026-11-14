"""Runtime check: real sale responses carry exactly the allow-listed keys (rule 6)."""

import pytest

from tests.contract.merchant_response_allow_list import ALLOWED_PROPERTIES_BY_SCHEMA
from tests.integration.api.api_harness import ApiHarness
from tests.integration.api.sale_api_helpers import (
    COUNTER_PATH,
    PHONE_64_GB_ID,
    SALES_PATH,
    TwoShops,
    mark_ready_to_pay_in_the_database,
    start_sale,
)

pytestmark = pytest.mark.integration


def test_counter_list_response_keys_equal_the_allow_list(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """A choosing and an agreed sale: list, sale and plan keys are exactly the allowed ones."""
    agreed_sale = start_sale(mock_api, shops.first_shop_headers)
    start_sale(mock_api, shops.first_shop_headers, PHONE_64_GB_ID)
    mark_ready_to_pay_in_the_database(mock_api, str(agreed_sale["saleId"]))
    body = mock_api.client.get(COUNTER_PATH, headers=shops.first_shop_headers).json()
    assert set(body) == ALLOWED_PROPERTIES_BY_SCHEMA["CounterSalesResponse"]
    assert len(body["sales"]) == 2
    for listed_sale in body["sales"]:
        assert set(listed_sale) == ALLOWED_PROPERTIES_BY_SCHEMA["SaleSummaryResponse"]
    chosen_plans = [sale["chosenPlan"] for sale in body["sales"] if sale["chosenPlan"] is not None]
    assert [set(chosen_plan) for chosen_plan in chosen_plans] == [
        ALLOWED_PROPERTIES_BY_SCHEMA["ChosenPlanResponse"]
    ]


def test_sale_detail_and_qr_response_keys_equal_the_allow_list(
    mock_api: ApiHarness, shops: TwoShops
) -> None:
    """POST /sales, GET /sales/{saleId} and POST .../qr-tokens carry only the allowed keys."""
    started_sale = start_sale(mock_api, shops.first_shop_headers)
    sale_path = f"{SALES_PATH}/{started_sale['saleId']}"
    detail = mock_api.client.get(sale_path, headers=shops.first_shop_headers).json()
    qr = mock_api.client.post(f"{sale_path}/qr-tokens", headers=shops.first_shop_headers).json()
    assert set(started_sale) == set(detail) == ALLOWED_PROPERTIES_BY_SCHEMA["SaleDetailResponse"]
    assert set(started_sale["qr"]) == ALLOWED_PROPERTIES_BY_SCHEMA["CustomerQrResponse"]
    assert set(qr) == ALLOWED_PROPERTIES_BY_SCHEMA["CustomerQrResponse"]
