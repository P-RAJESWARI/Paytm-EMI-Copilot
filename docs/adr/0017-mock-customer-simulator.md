# 0017: Labelled MockCustomerSimulator

Status: Accepted (owner, 2026-11-14: Layer 2 plan, step 2.3; CLAUDE.md rules 9 and 10).

## Context
In Layer 2 the customer app does not exist yet, but the demo and the Playwright path must reach "Ready to pay" and "Paid". The Mock gateway reports PAID only after 30 s on its clock.

## Decision
- `POST /api/v1/mock-customer-simulator/sales/{saleId}/agreed-plan` calls the same `MarkSaleReadyToPayService` that Layer 3 consent will call.
- `POST /api/v1/mock-customer-simulator/payments/{orderId}/completed` makes the Mock gateway produce a Mock-signed PAID notification and applies it through `PaymentStatusService.apply_webhook`; the sale moves through the normal events. Nothing sets a sale status directly.
- Both require the merchant token and check that the sale belongs to the caller.
- Registered only when `MOCK_CUSTOMER_SIMULATOR_ENABLED=true` (default false); refused at startup in paytm mode; announced in the startup log; left out of `openapi.json` (404 when disabled).

## Consequences
The simulator is a stand-in for the customer's own human gates and must never be enabled outside local demo and test runs. Layer 3 replaces its agree path with real consent.
