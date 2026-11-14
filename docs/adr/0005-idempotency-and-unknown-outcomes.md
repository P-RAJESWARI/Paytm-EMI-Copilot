# 0005: Idempotency and unknown outcomes on create-link

Status: Accepted (owner, 2026-11-14). Answers Layer 1 question 10.

## Decision
- `POST /payment-links` requires `Idempotency-Key`. We store the key with a SHA-256 fingerprint of the canonical request body.
- The same key with the same body returns the stored result. The same key with a different body returns 422 `IDEMPOTENCY_KEY_REUSED`.
- A create-link call is never retried. If it times out, the attempt is stored as `OUTCOME_UNKNOWN` and the request returns 504 `PAYMENT_GATEWAY_TIMEOUT`. A replay with the same key returns 409 `PAYMENT_LINK_OUTCOME_UNKNOWN`, and the caller starts again with a new key. Nothing is re-sent silently.
