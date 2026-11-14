# 0013: Merchant device pairing, tokens and rate limits

Status: Accepted (owner, 2026-11-14: Layer 2 plan Q10, Q16, Q18, Q20 defaults and the seed decision).

## Context
Merchant APIs need real authentication from Layer 2 onwards. The design's "owner app" that creates pairing PINs does not exist.

## Decision
- **Seed instead of an owner app:** `make seed` creates the demo shop RAVI-0193 ("Ravi Electronics", device label "Counter tablet 1") and its products. The PIN comes only from `DEMO_MERCHANT_PIN` in the environment; seeding fails if it is unset.
- **PIN:** stored as stdlib scrypt hash plus salt, compared in constant time. An unknown shop runs a decoy PIN check so it looks the same as a wrong PIN (same 401 `INVALID_PAIRING_CREDENTIALS`).
- **Lockout:** 5 consecutive wrong PINs lock the shop for 15 minutes (429 `PAIRING_TEMPORARILY_LOCKED`, `Retry-After`). The lockout state lives in the database.
- **Token:** opaque `secrets.token_urlsafe(32)`; only its SHA-256 is stored on `device_pairing`. Lifetime 12 h (`MERCHANT_ACCESS_TOKEN_LIFETIME_IN_SECONDS`), revocable. The browser keeps it in memory only, so a reload means pairing again.
- **Rate limits:** in-memory fixed windows (per client address for pairing and the webhook, per shop for gateway-backed merchant calls). This needs a single API worker.
- **Layer 1 endpoints:** `POST /payment-links` and `GET /payments/{orderId}/status` now need the merchant token; the status endpoint answers only for attempts of the caller's sales. `GET /offers` stays open; the webhook keeps signature auth.
- **Authorisation:** every merchant query is scoped `_for_merchant`; another shop's resource is 404.

## Consequences
- Lockout is counted per known shop, so with enough attempts someone can tell real shop IDs from unknown ones (unknown IDs never lock). The per-address limit slows this. Accepted for the demo; a production fix tracks failures for unknown IDs too.
- Anyone who knows a shop ID can lock that shop out for 15 minutes with 5 wrong PINs.
- The pairing limit is keyed by the peer address, so behind a proxy all devices share one bucket.
- In-memory limits reset on restart and do not work across several workers.
- Open: should the bare Layer 1 `POST /payment-links` (no sale) be retired? Its attempts can never be read back through the scoped status endpoint. Should idempotency keys be scoped per merchant?
