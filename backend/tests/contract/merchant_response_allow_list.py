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
)
"""Every merchant endpoint, the Layer 1 payment ones included since plan Q16; step 2.4 adds
/api/v1/reports."""

LAYER_1_GATEWAY_PATH_PREFIXES = ("/api/v1/offers", "/api/v1/webhooks/")
"""The unauthenticated Layer 1 gateway endpoints (ADR 0009); they carry no customer data."""

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
        "ProblemDetailsResponse": frozenset(
            {"type", "title", "status", "detail", "code", "correlationId", "fieldErrors"}
        ),
        "FieldErrorResponse": frozenset({"field", "message"}),
    }
)
"""Every schema reachable from a merchant response, with exactly the property names it has."""

SCHEMAS_ALLOWED_A_BUDGET_PROPERTY: frozenset[str] = frozenset()
"""Schemas that may name a budget: only step 2.4's aggregate report budget-bucket schema, which
counts customers per budget range and never shows one customer's budget. Empty until then."""
