"""OpenAPI examples and documented errors of the report endpoints (DESIGN_SPEC section 4 data)."""

from emi_copilot.api.openapi_documentation import ProblemExample

FUNNEL_REPORT_EXAMPLE = {
    "range": "THIS_WEEK",
    "periodStartDate": "2026-11-09",
    "periodEndDate": "2026-11-15",
    "stages": [
        {"stage": "STARTED", "customerCount": 120, "isSuppressed": False},
        {"stage": "BUDGET_TOLD", "customerCount": 96, "isSuppressed": False},
        {"stage": "PLANS_VIEWED", "customerCount": 88, "isSuppressed": False},
        {"stage": "AGREED", "customerCount": 51, "isSuppressed": False},
        {"stage": "PAID", "customerCount": 44, "isSuppressed": False},
    ],
    "biggestDrop": {"afterStage": "PLANS_VIEWED", "customerCount": 37, "isSuppressed": False},
}


EXAMPLE_CEILING_IN_RUPEES = 3000


def _bucket(
    lower_in_rupees: int,
    upper_in_rupees: int | None,
    customer_count: int,
    plans: list[dict[str, object]],
) -> dict[str, object]:
    """Builds one documented budget bucket under the ₹3,000 ceiling rule."""
    return {
        "lowerBoundInPaise": lower_in_rupees * 100,
        "upperBoundInPaise": None if upper_in_rupees is None else upper_in_rupees * 100,
        "customerCount": customer_count,
        "isSuppressed": False,
        "isUnderCeiling": upper_in_rupees is not None
        and upper_in_rupees <= EXAMPLE_CEILING_IN_RUPEES,
        "plans": plans,
    }


MISSED_SALES_EXAMPLE = {
    "range": "THIS_WEEK",
    "periodStartDate": "2026-11-09",
    "periodEndDate": "2026-11-15",
    "missedCustomerCount": 12,
    "isSuppressed": False,
    "budgetCeilingInPaise": 300_000,
    "productInsight": {
        "productId": "01JD5Z0Q8M6X3V2N7B4C9K1T0D",
        "productName": "Example phone, 128 GB",
        "lowestNoExtraCostMonthlyInPaise": 366_667,
        "cheapestPlanUnderCeiling": {
            "monthlyInstallmentInPaise": 205_000,
            "extraInTotalInPaise": 260_000,
        },
    },
    "budgetTotalCustomerCount": 96,
    "areBudgetBucketsHidden": False,
    "budgetBuckets": [
        _bucket(
            0,
            2500,
            5,
            [
                {
                    "planKind": "STANDARD",
                    "lenderLabel": "Demo cardless lender (Mock)",
                    "monthlyInstallmentInPaise": 205_000,
                }
            ],
        ),
        _bucket(2500, 3000, 7, []),
        _bucket(3000, 3500, 14, []),
        _bucket(
            3500,
            4000,
            21,
            [
                {
                    "planKind": "NO_COST",
                    "lenderLabel": "Brand",
                    "monthlyInstallmentInPaise": 366_667,
                },
                {
                    "planKind": "STANDARD",
                    "lenderLabel": "Your card's bank",
                    "monthlyInstallmentInPaise": 385_000,
                },
            ],
        ),
        _bucket(4000, None, 49, []),
    ],
}
SUGGESTED_ACTIONS_EXAMPLE = {
    "actions": [
        {
            "actionCode": "ASK_BRAND_FOR_LONGER_NO_COST_PLAN",
            "parameters": {
                "productId": "01JD5Z0Q8M6X3V2N7B4C9K1T0D",
                "productName": "Example phone, 128 GB",
                "currentNoCostTenureInMonths": 6,
                "currentNoCostMonthlyInPaise": 366_667,
                "suggestedTenures": [
                    {"tenureInMonths": 9, "monthlyInstallmentInPaise": 244_444},
                    {"tenureInMonths": 12, "monthlyInstallmentInPaise": 183_333},
                ],
                "missedCustomerCount": 12,
                "isMissedCustomerCountSuppressed": False,
                "budgetCeilingInPaise": 300_000,
            },
        },
        {
            "actionCode": "KEEP_CHEAPER_MODEL_READY",
            "parameters": {
                "productId": "01JD5Z0Q8M6X3V2N7B4C9K1T0E",
                "productName": "Example phone, 64 GB",
                "listPriceInPaise": 1_800_000,
                "monthlyInstallmentInPaise": 300_000,
                "tenureInMonths": 6,
            },
        },
    ]
}
MONEY_DUE_EXAMPLE = {
    "totalDueInPaise": 18_400_000,
    "nextExpectedDate": "2027-01-13",
    "batches": [
        {
            "batchNumber": 1,
            "saleCount": 18,
            "amountInPaise": 7_200_000,
            "expectedDate": "2027-01-13",
            "status": "CLAIM_FILED",
        },
        {
            "batchNumber": 2,
            "saleCount": 16,
            "amountInPaise": 6_400_000,
            "expectedDate": "2027-01-28",
            "status": "WAITING_FOR_BRAND",
        },
        {
            "batchNumber": 3,
            "saleCount": 10,
            "amountInPaise": 4_800_000,
            "expectedDate": "2027-02-12",
            "status": "NOT_YET_DUE",
        },
    ],
}
WEEKLY_MESSAGE_EXAMPLE = {
    "periodStartDate": "2026-11-09",
    "periodEndDate": "2026-11-15",
    "source": "TEMPLATE",
    "messages": {
        "en": {
            "title": "Your EMI sales, 9 to 15 November",
            "paragraphs": [
                "44 of 120 customers bought on EMI. The biggest drop was after seeing the plans.",
                "12 customers wanted under ₹3,000 a month with nothing extra, and no plan fit. "
                "₹1,84,000 is due from brands, first payment around 13 Jan.",
                "One thing to do: ask the brand for a 9 or 12-month no-cost plan on Example "
                "phone, 128 GB. That would be ₹2,444 or ₹1,833 a month.",
            ],
        },
        "ta": {
            "title": "உங்கள் EMI விற்பனை, 9 முதல் 15 நவம்பர்",
            "paragraphs": ["120 வாடிக்கையாளர்களில் 44 பேர் EMI-யில் வாங்கினர்."],
        },
    },
    "isSent": False,
    "sentAt": None,
}
SEND_WEEKLY_MESSAGE_REQUEST_EXAMPLE = {"periodStartDate": "2026-11-09"}
INVALID_REPORTING_PERIOD_PROBLEM = ProblemExample(
    422,
    "INVALID_REPORTING_PERIOD",
    "Invalid reporting period",
    "A reporting week starts on a Monday.",
    "periodStartDate is not a Monday, or names a week that has not started yet.",
)
