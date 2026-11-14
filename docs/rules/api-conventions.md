# api-conventions.md: REST API conventions

The API contract is defined by Pydantic DTOs and published as OpenAPI. The frontend client is generated from it, so the schema is the single source of truth.

## 1. Basics

- Base path `/api/v1`. Breaking change means `/api/v2`; additive change stays in v1.
- JSON only. **Wire format is camelCase**; Python code stays `snake_case` (Pydantic alias generator).
- Resources are plural nouns: `/sales`, `/sales/{saleId}/plans`. Actions that are not CRUD use a verb sub-resource: `POST /sales/{saleId}/consent`.
- Timestamps: ISO 8601 in UTC (`2026-11-15T09:30:00Z`). Display conversion is a frontend concern.
- IDs: opaque strings (ULID or UUID). Never expose database sequence numbers.

## 2. Money

- Always an integer **in paise** with an explicit field name: `monthlyInstallmentInPaise`, `extraInTotalInPaise`, `priceInPaise`. Currency is INR and implicit; no currency field unless a second currency is ever introduced.
- Never send floats, formatted strings or "₹" symbols for money.
- Percentages (comfort ratio) are sent as an integer in basis points: `comfortRatioInBasisPoints: 3890` means 38.90%.

## 3. Status codes

| Code | Use |
|---|---|
| 200 | Successful read or action |
| 201 | Resource created (include `Location`) |
| 202 | Accepted for asynchronous processing (payment handoff pending) |
| 204 | Success with no body |
| 400 | Malformed request |
| 401 | Missing or invalid credentials or QR token |
| 403 | Authenticated but not allowed (for example another merchant's sale) |
| 404 | Not found (also used when hiding existence for privacy) |
| 409 | State conflict (consent already given, sale already paid) |
| 422 | Valid JSON but fails validation or a business rule |
| 429 | Rate limited (include `Retry-After`) |
| 502/504 | Upstream gateway or AI failure surfaced as a problem response |

## 4. Errors: RFC 7807 problem+json

```json
{
  "type": "https://emicopilot.example/problems/offer-not-found",
  "title": "Offer not found",
  "status": 404,
  "detail": "No offer matches the requested product and price.",
  "code": "OFFER_NOT_FOUND",
  "correlationId": "01J...",
  "fieldErrors": [{ "field": "priceInPaise", "message": "Must be greater than zero" }]
}
```

`code` is a stable machine-readable value the frontend maps to translated text. `detail` is English for developers and never shown to customers verbatim. No stack traces, SQL, vendor payloads or personal data.

## 5. Headers

| Header | Rule |
|---|---|
| `X-Correlation-Id` | Accepted if present, generated if not, echoed in the response and in every log line |
| `Idempotency-Key` | **Required** on `POST` calls that create payment links, initiate payments or record consent. Same key plus same body returns the original result; same key plus different body returns 422 |
| `Authorization: Bearer <merchant-token>` | Merchant endpoints |
| `X-Customer-Session-Token` | Customer endpoints; short-lived, single-sale, from the QR |
| `Accept-Language` | `en` or `ta`; affects only human-readable text such as explanations |

## 6. Authentication and authorisation

- **Merchant:** device pairing with a PIN issues a short-lived bearer token (details in Layer 2). A merchant can only read their own sales.
- **Customer:** the QR contains a signed, expiring, single-use-to-exchange token that is traded for a session token bound to one sale. Tokens are never logged.
- Rate limits on token exchange, OTP request, OTP verify and consent endpoints.

## 7. Planned endpoint groups (filled in per layer)

| Layer | Group | Examples |
|---|---|---|
| 1 | Gateway | `GET /offers`, `POST /payment-links`, `GET /payments/{orderId}/status`, `POST /webhooks/paytm` |
| 2 | Merchant | `POST /merchants/pairing`, `GET /products`, `POST /sales`, `GET /sales`, `GET /reports/funnel`, `GET /reports/missed-sales`, `GET /reports/money-due` |
| 3 | Customer | `POST /customer-sessions`, `PUT /customer-sessions/{id}/budget`, `POST .../comfort-check`, `GET .../plans`, `POST .../alternatives`, `POST .../consent`, `GET .../receipt` |
| 4 | AI | `POST .../explanation`, `POST .../speech/transcriptions`, `POST .../speech/synthesis`, `POST .../teach-back`, `GET /reports/weekly-message` |

## 8. Webhooks

- Verify the Paytm signature before parsing the body; reject on mismatch with 401 and log a security event.
- Handlers are idempotent: processing the same event twice has no extra effect.
- Respond quickly (202) and process through the event bus.

## 9. Documentation

Every endpoint has a summary, a description, example request and response bodies, and its error codes in the OpenAPI schema. `make openapi` exports `openapi.json`; the frontend client is regenerated from it, and CI fails if the committed client is out of date.
