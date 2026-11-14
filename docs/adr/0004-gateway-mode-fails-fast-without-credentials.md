# 0004: Gateway mode `paytm` without credentials fails fast

Status: Accepted (owner, 2026-11-14). Answers Layer 1 question 9.

## Decision
`PaymentGatewayFactory` returns the Mock when `PAYMENT_GATEWAY_MODE=mock` (the default). With `PAYMENT_GATEWAY_MODE=paytm`, startup **fails** with a clear configuration error if the merchant ID, merchant key or base URLs are missing. It does not silently fall back to the Mock. The active adapter is announced in the startup log.

## Consequences
Nobody can believe real payments are live while the Mock is running. design-patterns.md is updated to match.
