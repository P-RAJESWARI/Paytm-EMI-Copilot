"""The exact response fields merchant endpoints may expose (CLAUDE.md rule 6).

A merchant sees sale status, the chosen plan, totals and aggregates; never a customer's income,
existing EMIs, comfort ratio, budget or step-by-step progress. Adding a field to a merchant
response means adding it here on purpose, where a reviewer sees it.
"""

from collections.abc import Mapping
from types import MappingProxyType

MERCHANT_PATH_PREFIXES = (
    "/api/v1/merchants",
    "/api/v1/products",
    "/api/v1/sales",
    "/api/v1/payment-links",
    "/api/v1/payments/",
    "/api/v1/reports",
)
"""Every merchant endpoint, the Layer 1 payment ones included since plan Q16, and the step 2.4
reports."""

LAYER_1_GATEWAY_PATH_PREFIXES = ("/api/v1/offers", "/api/v1/webhooks/")
"""The unauthenticated Layer 1 gateway endpoints (ADR 0009); they carry no customer data."""

CUSTOMER_PATH_PREFIXES = ("/api/v1/customer-sessions",)
"""The customer's own endpoints (Layer 3): only the customer's session token opens them, so they
may show the customer their own figures; no merchant response may reach their schemas."""

MERCHANT_SALE_STATUSES = ("CHOOSING", "READY_TO_PAY", "PAID", "PAYMENT_NOT_COMPLETED", "EXPIRED")
"""Plan Q2: the five sale statuses a merchant may see, and no customer step."""

SALE_SUMMARY_FIELDS = frozenset(
    {
        "saleId",
        "sessionCode",
        "productName",
        "priceInPaise",
        "status",
        "statusChangedAt",
        "chosenPlan",
    }
)

ALLOWED_PROPERTIES_BY_SCHEMA: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "DevicePairingResponse": frozenset({"accessToken", "tokenType", "expiresAt", "merchant"}),
        "MerchantProfileResponse": frozenset({"merchantId", "shopId", "shopName", "deviceLabel"}),
        "ProductsResponse": frozenset({"products"}),
        "CatalogueProductResponse": frozenset(
            {"productId", "name", "listPriceInPaise", "planCount", "noExtraCostPlanCount"}
        ),
        "CounterSalesResponse": frozenset({"sales"}),
        "SaleSummaryResponse": SALE_SUMMARY_FIELDS,
        "SaleDetailResponse": SALE_SUMMARY_FIELDS | {"productId", "startedAt", "qr"},
        "ChosenPlanResponse": frozenset(
            {
                "offerId",
                "planKind",
                "lenderLabel",
                "tenureInMonths",
                "monthlyInstallmentInPaise",
                "extraInTotalInPaise",
                "totalPayableInPaise",
            }
        ),
        "CustomerQrResponse": frozenset({"customerUrl", "expiresAt"}),
        "SaleHandoffResponse": frozenset(
            {"sale", "edcInstructions", "latestPaymentLink", "paymentStatus", "paymentConfirmedAt"}
        ),
        "EdcInstructionsResponse": frozenset(
            {"emiProgramme", "productName", "tenureInMonths", "isNoExtraCost", "amountInPaise"}
        ),
        "LatestPaymentLinkResponse": frozenset({"orderId", "paymentUrl", "status"}),
        "SalePaymentLinkResponse": frozenset({"orderId", "paymentUrl", "amountInPaise", "status"}),
        "SalePaymentStatusResponse": frozenset({"paymentStatus", "paymentConfirmedAt"}),
        "PaymentLinkResponse": frozenset({"orderId", "paymentUrl", "status", "offer"}),
        "OfferSnapshotResponse": frozenset(
            {
                "offerId",
                "lenderLabel",
                "emiType",
                "tenureInMonths",
                "regularInstallmentInPaise",
                "lastInstallmentInPaise",
                "extraInTotalInPaise",
                "totalPayableInPaise",
                "priceInPaise",
            }
        ),
        "PaymentStatusResponse": frozenset({"orderId", "status", "amountPaidInPaise"}),
        "SaleStatusEventPayload": frozenset({"saleId", "status", "statusChangedAt"}),
        "SaleStatus": frozenset(),
        "EmiType": frozenset(),
        "EdcEmiProgramme": frozenset(),
        "HandoffPaymentStatus": frozenset(),
        "PublicPaymentStatus": frozenset(),
        "FunnelReportResponse": frozenset(
            {"range", "periodStartDate", "periodEndDate", "stages", "biggestDrop"}
        ),
        "FunnelStageCountResponse": frozenset({"stage", "customerCount", "isSuppressed"}),
        "FunnelDropResponse": frozenset({"afterStage", "customerCount", "isSuppressed"}),
        "MissedSalesReportResponse": frozenset(
            {
                "range",
                "periodStartDate",
                "periodEndDate",
                "missedCustomerCount",
                "isSuppressed",
                "budgetCeilingInPaise",
                "productInsight",
                "budgetTotalCustomerCount",
                "areBudgetBucketsHidden",
                "budgetBuckets",
            }
        ),
        "ProductInsightResponse": frozenset(
            {
                "productId",
                "productName",
                "lowestNoExtraCostMonthlyInPaise",
                "cheapestPlanUnderCeiling",
            }
        ),
        "CheapestPlanUnderCeilingResponse": frozenset(
            {"monthlyInstallmentInPaise", "extraInTotalInPaise"}
        ),
        "BudgetBucketResponse": frozenset(
            {
                "lowerBoundInPaise",
                "upperBoundInPaise",
                "customerCount",
                "isSuppressed",
                "isUnderCeiling",
                "plans",
            }
        ),
        "BucketPlanResponse": frozenset({"planKind", "lenderLabel", "monthlyInstallmentInPaise"}),
        "SuggestedActionsResponse": frozenset({"actions"}),
        "LongerNoCostPlanActionResponse": frozenset({"actionCode", "parameters"}),
        "LongerNoCostPlanParametersResponse": frozenset(
            {
                "productId",
                "productName",
                "currentNoCostTenureInMonths",
                "currentNoCostMonthlyInPaise",
                "suggestedTenures",
                "missedCustomerCount",
                "isMissedCustomerCountSuppressed",
                "budgetCeilingInPaise",
            }
        ),
        "SuggestedNoCostTenureResponse": frozenset({"tenureInMonths", "monthlyInstallmentInPaise"}),
        "CheaperModelActionResponse": frozenset({"actionCode", "parameters"}),
        "CheaperModelParametersResponse": frozenset(
            {
                "productId",
                "productName",
                "listPriceInPaise",
                "monthlyInstallmentInPaise",
                "tenureInMonths",
            }
        ),
        "MoneyDueResponse": frozenset({"totalDueInPaise", "nextExpectedDate", "batches"}),
        "BrandSettlementBatchResponse": frozenset(
            {"batchNumber", "saleCount", "amountInPaise", "expectedDate", "status"}
        ),
        "WeeklyMessageResponse": frozenset(
            {"periodStartDate", "periodEndDate", "source", "messages", "isSent", "sentAt"}
        ),
        "WeeklyMessageLanguagesResponse": frozenset({"en", "ta"}),
        "WeeklyMessageTextResponse": frozenset({"title", "paragraphs"}),
        "ReportingRange": frozenset(),
        "FunnelStage": frozenset(),
        "BrandSettlementStatus": frozenset(),
        "ProblemDetailsResponse": frozenset(
            {"type", "title", "status", "detail", "code", "correlationId", "fieldErrors"}
        ),
        "FieldErrorResponse": frozenset({"field", "message"}),
    }
)
"""Every schema reachable from a merchant response, with exactly the property names it has."""

SCHEMAS_ALLOWED_A_BUDGET_PROPERTY: frozenset[str] = frozenset(
    {"MissedSalesReportResponse", "LongerNoCostPlanParametersResponse"}
)
"""Schemas that may name a budget, all aggregates of step 2.4's missed-sales report: the
budget-range counts (budgetBuckets, budgetTotalCustomerCount, areBudgetBucketsHidden) and the
range boundary over every missed amount (budgetCeilingInPaise, which the longer no-cost
suggestion repeats). None shows one customer's budget; BudgetBucketResponse itself names no
budget property."""
