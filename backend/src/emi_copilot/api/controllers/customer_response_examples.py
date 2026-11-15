"""Documented success bodies of the customer flow: a real run of the services, ids replaced.

They come from the main application on PostgreSQL at 2026-11-15T09:30:00Z with the design data
(Ravi Electronics, the ₹22,000 phone on the Mock gateway, ₹3,000 budget, comfort check allowed
with the synthetic profile, the no-cost plan explained and agreed, reference serial 42); the
session summary is read last. An integration test replays that run and requires these bodies
(ids, tokens and the random session code aside), so the documented numbers cannot drift.
"""

from typing import Any

EXAMPLE_CUSTOMER_SESSION_ID = "01JD5Z0Q8M6X3V2N7B4C9K1T0E"
EXAMPLE_PHONE_128_GB_PRODUCT_ID = "01JD5Z0Q8M6X3V2N7B4C9K1T0F"
EXAMPLE_PHONE_64_GB_PRODUCT_ID = "01JD5Z0Q8M6X3V2N7B4C9K1T0G"
EXAMPLE_CONSENTED_PLAN: dict[str, Any] = {
    "offerId": "mock-offer-no-cost-6m",
    "lenderLabel": "Brand",
    "emiType": "NO_COST",
    "tenureInMonths": 6,
    "regularInstallmentInPaise": 366667,
    "lastInstallmentInPaise": 366665,
    "extraInTotalInPaise": 0,
    "totalPayableInPaise": 2200000,
    "priceInPaise": 2200000,
    "productId": EXAMPLE_PHONE_128_GB_PRODUCT_ID,
    "productName": "Example phone, 128 GB",
    "downPaymentInPaise": 0,
    "financedAmountInPaise": 2200000,
}

CUSTOMER_SESSION_RESPONSE_EXAMPLE: dict[str, Any] = {
    "customerSessionId": EXAMPLE_CUSTOMER_SESSION_ID,
    "sessionToken": "<session-token>",
    "sessionCode": "4821",
    "shopName": "Ravi Electronics",
    "productName": "Example phone, 128 GB",
    "priceInPaise": 2200000,
    "expiresAt": "2026-11-15T10:00:00Z",
}
BUDGET_RESPONSE_EXAMPLE: dict[str, Any] = {
    "monthlyBudgetInPaise": 300000,
    "hasCustomerConfirmed": True,
}
COMFORT_CHECK_RESPONSE_EXAMPLE: dict[str, Any] = {
    "status": "COMPLETED",
    "isSyntheticData": True,
    "monthlyInflowInPaise": 3000000,
    "existingEmisInPaise": 800000,
}
PLANS_RESPONSE_EXAMPLE: dict[str, Any] = {
    "monthlyBudgetInPaise": 300000,
    "hasAnyPlanWithinBudget": True,
    "hasComfortCheck": True,
    "plans": [
        {
            "position": 1,
            "offerId": "mock-offer-cardless-12m",
            "lenderLabel": "Demo cardless lender (Mock)",
            "emiType": "STANDARD",
            "tenureInMonths": 12,
            "monthlyInstallmentInPaise": 205000,
            "lastInstallmentInPaise": 205000,
            "extraInTotalInPaise": 260000,
            "totalPayableInPaise": 2460000,
            "priceInPaise": 2200000,
            "isWithinBudget": True,
            "amountAboveBudgetInPaise": 0,
            "reasonCodes": ["WITHIN_BUDGET", "LOWEST_MONTHLY_AMOUNT"],
            "comfort": {
                "band": "COMFORTABLE",
                "comfortRatioInBasisPoints": 3350,
                "planShareInBasisPoints": 683,
                "existingEmisShareInBasisPoints": 2667,
            },
        },
        {
            "position": 2,
            "offerId": "mock-offer-no-cost-6m",
            "lenderLabel": "Brand",
            "emiType": "NO_COST",
            "tenureInMonths": 6,
            "monthlyInstallmentInPaise": 366667,
            "lastInstallmentInPaise": 366665,
            "extraInTotalInPaise": 0,
            "totalPayableInPaise": 2200000,
            "priceInPaise": 2200000,
            "isWithinBudget": False,
            "amountAboveBudgetInPaise": 66667,
            "reasonCodes": ["ABOVE_BUDGET", "NO_EXTRA_COST", "LOWEST_EXTRA_IN_TOTAL"],
            "comfort": {
                "band": "STRETCHING",
                "comfortRatioInBasisPoints": 3889,
                "planShareInBasisPoints": 1222,
                "existingEmisShareInBasisPoints": 2667,
            },
        },
        {
            "position": 3,
            "offerId": "mock-offer-card-6m",
            "lenderLabel": "Your card's bank",
            "emiType": "STANDARD",
            "tenureInMonths": 6,
            "monthlyInstallmentInPaise": 385000,
            "lastInstallmentInPaise": 385000,
            "extraInTotalInPaise": 110000,
            "totalPayableInPaise": 2310000,
            "priceInPaise": 2200000,
            "isWithinBudget": False,
            "amountAboveBudgetInPaise": 85000,
            "reasonCodes": ["ABOVE_BUDGET"],
            "comfort": {
                "band": "STRETCHING",
                "comfortRatioInBasisPoints": 3950,
                "planShareInBasisPoints": 1283,
                "existingEmisShareInBasisPoints": 2667,
            },
        },
    ],
}
PLAN_ALTERNATIVES_RESPONSE_EXAMPLE: dict[str, Any] = {
    "basePlan": {
        "offerId": "mock-offer-no-cost-6m",
        "lenderLabel": "Brand",
        "emiType": "NO_COST",
        "tenureInMonths": 6,
        "monthlyInstallmentInPaise": 366667,
        "lastInstallmentInPaise": 366665,
        "extraInTotalInPaise": 0,
        "totalPayableInPaise": 2200000,
        "priceInPaise": 2200000,
        "isWithinBudget": False,
        "amountAboveBudgetInPaise": 66667,
        "comfort": {
            "band": "STRETCHING",
            "comfortRatioInBasisPoints": 3889,
            "planShareInBasisPoints": 1222,
            "existingEmisShareInBasisPoints": 2667,
        },
    },
    "hasLowerMonthlyAlternative": True,
    "alternatives": [
        {
            "kind": "DOWN_PAYMENT",
            "offerId": "mock-offer-no-cost-6m",
            "tenureInMonths": 6,
            "downPaymentInPaise": 400000,
            "financedAmountInPaise": 1800000,
            "productId": None,
            "productName": None,
            "priceInPaise": 2200000,
            "monthlyInstallmentInPaise": 300000,
            "previousMonthlyInstallmentInPaise": 366667,
            "extraInTotalInPaise": 0,
            "totalPayableInPaise": 1800000,
            "isLowerMonthlyAmount": True,
            "isWithinBudget": True,
            "comfort": {
                "band": "STRETCHING",
                "comfortRatioInBasisPoints": 3667,
                "planShareInBasisPoints": 1000,
                "existingEmisShareInBasisPoints": 2667,
            },
        },
        {
            "kind": "LONGER_TENURE",
            "offerId": "mock-offer-cardless-12m",
            "tenureInMonths": 12,
            "downPaymentInPaise": 0,
            "financedAmountInPaise": 2200000,
            "productId": None,
            "productName": None,
            "priceInPaise": 2200000,
            "monthlyInstallmentInPaise": 205000,
            "previousMonthlyInstallmentInPaise": 366667,
            "extraInTotalInPaise": 260000,
            "totalPayableInPaise": 2460000,
            "isLowerMonthlyAmount": True,
            "isWithinBudget": True,
            "comfort": {
                "band": "COMFORTABLE",
                "comfortRatioInBasisPoints": 3350,
                "planShareInBasisPoints": 683,
                "existingEmisShareInBasisPoints": 2667,
            },
        },
        {
            "kind": "CHEAPER_MODEL",
            "offerId": "mock-offer-no-cost-6m",
            "tenureInMonths": 6,
            "downPaymentInPaise": 0,
            "financedAmountInPaise": 1800000,
            "productId": EXAMPLE_PHONE_64_GB_PRODUCT_ID,
            "productName": "Example phone, 64 GB",
            "priceInPaise": 1800000,
            "monthlyInstallmentInPaise": 300000,
            "previousMonthlyInstallmentInPaise": 366667,
            "extraInTotalInPaise": 0,
            "totalPayableInPaise": 1800000,
            "isLowerMonthlyAmount": True,
            "isWithinBudget": True,
            "comfort": {
                "band": "STRETCHING",
                "comfortRatioInBasisPoints": 3667,
                "planShareInBasisPoints": 1000,
                "existingEmisShareInBasisPoints": 2667,
            },
        },
    ],
}
PLAN_EXPLANATION_RESPONSE_EXAMPLE: dict[str, Any] = {
    "text": (
        "No-cost EMI: you pay ₹3,667 each month for 6 months. The extra you pay in total is ₹0, "
        "so nothing is added to the price."
    ),
    "language": "en",
    "source": "TEMPLATE",
    "highlightedAmounts": [
        {"kind": "MONTHLY_INSTALLMENT", "amountInPaise": 366667},
        {"kind": "EXTRA_IN_TOTAL", "amountInPaise": 0},
    ],
}
OTP_CHALLENGE_RESPONSE_EXAMPLE: dict[str, Any] = {
    "phoneLastTwoDigits": "42",
    "expiresAt": "2026-11-15T09:35:00Z",
    "resendAvailableAt": "2026-11-15T09:30:30Z",
    "attemptsRemaining": 3,
}
CONSENT_RESPONSE_EXAMPLE: dict[str, Any] = {
    "consentId": "01JD5Z0Q8M6X3V2N7B4C9K1T0D",
    "reference": "EMI-1511-0042",
    "consentedAt": "2026-11-15T09:30:00Z",
    "status": "READY_TO_PAY",
    "plan": EXAMPLE_CONSENTED_PLAN,
}
RECEIPT_RESPONSE_EXAMPLE: dict[str, Any] = {
    "status": "READY_TO_PAY",
    "reference": "EMI-1511-0042",
    "phoneLastTwoDigits": "42",
    "consentedAt": "2026-11-15T09:30:00Z",
    "coolingOffNoticeStatus": "PLACEHOLDER",
    "plan": EXAMPLE_CONSENTED_PLAN,
}
CUSTOMER_SESSION_SUMMARY_RESPONSE_EXAMPLE: dict[str, Any] = {
    "customerSessionId": EXAMPLE_CUSTOMER_SESSION_ID,
    "sessionCode": "4821",
    "shopName": "Ravi Electronics",
    "productName": "Example phone, 128 GB",
    "priceInPaise": 2200000,
    "expiresAt": "2026-11-15T10:00:00Z",
    "hasConfirmedBudget": True,
    "comfortCheckStatus": "COMPLETED",
    "hasConsented": True,
}
