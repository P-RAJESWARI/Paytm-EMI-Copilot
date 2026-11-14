"""OpenAPI examples and documented errors of the sale endpoints (kept out of the controller)."""

from emi_copilot.api.openapi_documentation import ProblemExample

EXAMPLE_SALE_ID = "01JD5Z0Q8M6X3V2N7B4C9K1T0F"
EXAMPLE_PRODUCT_ID = "01JD5Z0Q8M6X3V2N7B4C9K1T0D"
START_SALE_REQUEST_EXAMPLE = {"productId": EXAMPLE_PRODUCT_ID}
CUSTOMER_QR_EXAMPLE = {
    "customerUrl": "http://localhost:5174/#t=<signed-token>",
    "expiresAt": "2026-11-15T09:45:00Z",
}
NO_COST_CHOSEN_PLAN_EXAMPLE = {
    "offerId": "mock-offer-no-cost-6m",
    "planKind": "NO_COST",
    "lenderLabel": "Brand",
    "tenureInMonths": 6,
    "monthlyInstallmentInPaise": 366_667,
    "extraInTotalInPaise": 0,
    "totalPayableInPaise": 2_200_000,
}
CHOOSING_SALE_SUMMARY_EXAMPLE = {
    "saleId": EXAMPLE_SALE_ID,
    "sessionCode": "4821",
    "productName": "Example phone, 128 GB",
    "priceInPaise": 2_200_000,
    "status": "CHOOSING",
    "statusChangedAt": "2026-11-15T09:30:00Z",
    "chosenPlan": None,
}
STARTED_SALE_EXAMPLE = {
    **CHOOSING_SALE_SUMMARY_EXAMPLE,
    "productId": EXAMPLE_PRODUCT_ID,
    "startedAt": "2026-11-15T09:30:00Z",
    "qr": CUSTOMER_QR_EXAMPLE,
}
READY_TO_PAY_SALE_DETAIL_EXAMPLE = {
    **STARTED_SALE_EXAMPLE,
    "status": "READY_TO_PAY",
    "statusChangedAt": "2026-11-15T09:36:00Z",
    "chosenPlan": NO_COST_CHOSEN_PLAN_EXAMPLE,
    "qr": None,
}
COUNTER_SALES_EXAMPLE = {
    "sales": [
        {
            **CHOOSING_SALE_SUMMARY_EXAMPLE,
            "saleId": "01JD5Z0Q8M6X3V2N7B4C9K1T0G",
            "sessionCode": "0917",
            "productName": "Example phone, 64 GB",
            "priceInPaise": 1_800_000,
            "statusChangedAt": "2026-11-15T09:41:00Z",
        },
        {
            **CHOOSING_SALE_SUMMARY_EXAMPLE,
            "status": "READY_TO_PAY",
            "statusChangedAt": "2026-11-15T09:36:00Z",
            "chosenPlan": NO_COST_CHOSEN_PLAN_EXAMPLE,
        },
    ]
}
IDEMPOTENCY_KEY_DESCRIPTION = (
    "Optional. 8 to 255 visible ASCII characters (a UUID or ULID is ideal). The same key with the "
    "same body returns the original sale, as it now stands, with qr null (raw QR tokens are never "
    "kept; ask POST .../qr-tokens for a new one); with a different body it is refused with 422 "
    "IDEMPOTENCY_KEY_REUSED. Keys are scoped to the shop."
)
PRODUCT_NOT_FOUND_PROBLEM = ProblemExample(
    404,
    "PRODUCT_NOT_FOUND",
    "Product not found",
    "No product with this id is in the shop's catalogue.",
    "The product is not in the signed-in shop's catalogue (another shop's looks the same).",
)
SALE_NOT_FOUND_PROBLEM = ProblemExample(
    404,
    "SALE_NOT_FOUND",
    "Sale not found",
    "No sale with this id belongs to the shop.",
    "The sale is not one of the signed-in shop's sales (another shop's looks the same).",
)
SESSION_CODES_EXHAUSTED_PROBLEM = ProblemExample(
    409,
    "SESSION_CODES_EXHAUSTED",
    "No free session code",
    "Every session code is on one of the shop's open sales.",
    "All 10,000 four-digit codes are on the shop's open sales; finish or wait for some first.",
)
SALE_STATE_CONFLICT_PROBLEM = ProblemExample(
    409,
    "SALE_STATE_CONFLICT",
    "Not possible in the sale's current status",
    "A sale that is READY_TO_PAY cannot take the command ISSUE_QR_CODE.",
    "A new QR code is issued only while the customer is CHOOSING.",
)
IDEMPOTENCY_KEY_REUSED_PROBLEM = ProblemExample(
    422,
    "IDEMPOTENCY_KEY_REUSED",
    "Idempotency key reused",
    "The Idempotency-Key was used with a different body.",
    "The Idempotency-Key was already used by this shop with a different body.",
)
