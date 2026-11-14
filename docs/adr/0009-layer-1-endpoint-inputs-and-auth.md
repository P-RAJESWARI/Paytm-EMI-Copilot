# 0009: Layer 1 endpoint inputs and authentication

Status: Accepted (owner, 2026-11-14, as a stated default).

## Decision
- Layer 1 gateway endpoints are **unauthenticated**, and the OpenAPI descriptions say so. Merchant auth arrives in Layer 2. The webhook is authenticated by its Paytm checksum.
- `GET /api/v1/offers` takes `priceInPaise`, `productId`, `brandId` and `categoryId`, because Paytm's item-based EMI APIs need them.
- `payment_attempt` has no `sale_id` column yet. Layer 2 adds it with its own migration.
