# 0015: Customer QR token

Status: Accepted (owner, 2026-11-14: Layer 2 plan, step 2.2 and Q18).

## Decision
- The QR encodes `{CUSTOMER_WEB_BASE_URL}/#t=<token>`. The token is in the URL fragment, so it never reaches a server log.
- The token is HMAC-SHA256 over `{saleId, nonce, expiresAt}`, base64url, verified in constant time. Lifetime 15 minutes (`CUSTOMER_QR_TOKEN_LIFETIME_IN_SECONDS`).
- Only the nonce hash and expiry are stored on the sale; issuing a new QR (`POST /sales/{id}/qr-tokens`, CHOOSING only) replaces the hash and voids the old token. `qr_token_exchanged_at` is filled by the Layer 3 exchange.
- `CUSTOMER_QR_SIGNING_SECRET` comes from the environment. In Mock mode an unset secret is replaced by a random per-process key with a startup warning; in paytm mode startup fails without it.
- The 4-digit session code is for display only and is never a credential.
- A replayed `POST /sales` (same Idempotency-Key) returns `qr: null`, because raw tokens are never stored; the client asks for a fresh QR.
