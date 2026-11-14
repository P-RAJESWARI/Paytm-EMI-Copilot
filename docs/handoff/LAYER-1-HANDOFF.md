# LAYER-1-HANDOFF: Foundation + Payment gateway integration

Branch `layer/1-payment-gateway`, 2026-11-14. This file doubles as the MR description (git-workflow.md section 4).

## What was built

**Backend skeleton:** FastAPI app factory, typed settings, JSON logs with correlation ids and redaction, Docker Compose PostgreSQL 16, Makefile (`setup`, `dev`, `check`, `test`, `migrate`, `openapi`), pre-commit, `/health`.

**Domain:**
- `Money` (Decimal, half-up to paise, no float, no negatives).
- EMI strategies (no-cost, quoted-total, reducing-balance).
- Payment types, domain events, and a table of legal payment-attempt status changes.

**Persistence:** `payment_attempt` (with the idempotency key and request fingerprint) and append-only `audit_event`. A database trigger blocks UPDATE, DELETE and TRUNCATE on `audit_event`. Alembic migrations 0001 and 0002; repositories plus a unit of work.

**Gateway:**
- `PaymentGatewayPort`, written in our own terms.
- `MockPaymentGatewayAdapter` (the default, announced at startup).
- `PaytmPaymentGatewayAdapter` (checksum signer, payload mapper, error translator), tested only against fixtures.
- A resilient HTTP client: jittered retry for reads only, a circuit breaker per host, TLS 1.2+ with verification.
- `PaymentGatewayFactory`: `PAYMENT_GATEWAY_MODE=paytm` without credentials fails at startup.

**Services:** `OfferDiscoveryService` (with the ₹1 quote cross-check audit), `PaymentHandoffService` (idempotent, two transactions, create is never retried) and `PaymentStatusService` (server-side status and an idempotent webhook).

**API (`/api/v1`, unauthenticated in Layer 1 per ADR 0009):**

| Method | Path | Result |
|---|---|---|
| GET | `/offers?priceInPaise&productId&brandId&categoryId` | 200 |
| POST | `/payment-links` | 201; needs `Idempotency-Key` |
| GET | `/payments/{orderId}/status` | 200 |
| POST | `/webhooks/paytm` | 202; 401 on a bad signature |

Errors use RFC 7807 problem+json. `backend/openapi.json` is exported by `make openapi`.

## Why (decisions, with ADR links)

| ADR | Decision |
|---|---|
| [0001](../adr/0001-emi-quoted-total-strategy-and-paise-rounding.md) | Quoted-total strategy; paise rounding with rupee display; the lender's figure is shown and mismatches are audited |
| [0002](../adr/0002-paytm-api-mapping.md) | Paytm API mapping (Banks → Tenures, Create Link, v3 status, webhook) |
| [0003](../adr/0003-paytm-checksum-implementation.md) | Checksum ported to `cryptography` and cross-tested against the official library |
| [0004](../adr/0004-gateway-mode-fails-fast-without-credentials.md) | Paytm mode without credentials fails fast |
| [0005](../adr/0005-idempotency-and-unknown-outcomes.md) | Idempotency key plus fingerprint; OUTCOME_UNKNOWN; never re-sent |
| [0006](../adr/0006-settlement-port-moves-to-layer-2.md) | SettlementPort moves to Layer 2 |
| [0007](../adr/0007-test-database-coverage-and-fixtures.md) | Compose test database; coverage gates; documented-shape fixtures |
| [0008](../adr/0008-tooling-naming-and-libraries.md) | Tooling, naming, libraries; composition root |
| [0009](../adr/0009-layer-1-endpoint-inputs-and-auth.md) | Endpoint inputs; no auth in Layer 1 |
| [0010](../adr/0010-paytm-link-fields-subvention-extra-and-unknown-outcomes.md) | Omit `partialPayment`/`bindLinkIdMobile`; subvention extra = interest − gratification; HTTP 5xx and timeouts mean outcome unknown |
| [0011](../adr/0011-paytm-status-codes-partial-discovery-and-quote-check.md) | Status codes 334/335/501 are not payment failures; link codes 501/502 are rejected (owner); partial discovery fails the whole call; quote check runs in the service |

## Patterns used

| Pattern | File | Problem solved |
|---|---|---|
| Value Object | `domain/money.py`, `domain/emi/emi_schedule.py`, `domain/payments/offer_snapshot.py` | Rounding and the no-float rule in one place; invalid states impossible |
| Strategy | `domain/emi/*_strategy.py` | Rules for no-cost, quoted-total and reducing-balance vary independently |
| Repository + Unit of Work | `repositories/*` | No SQL in services; the attempt and its audit row commit together |
| Port and Adapter | `adapters/payment_gateway/port.py`, `mock_adapter.py`, `paytm_adapter.py` | Mock and Paytm swap by configuration; one contract suite runs against both |
| Factory | `adapters/payment_gateway/factory.py` | One place picks the adapter, logs the choice and fails fast |
| Retry + Circuit Breaker | `core/resilient_http_client.py`, `core/circuit_breaker.py` | A slow gateway cannot starve the app; create is never retried |
| Observer | `events/event_bus.py`, `events/audit_subscriber.py` | Audit (and the Layer 2 status feed) stays decoupled from services |
| Table-driven transitions | `domain/payments/payment_attempt_transitions.py` | Repeated and late webhooks are safe; PAID is terminal |
| DTO | `dtos/*` | The camelCase, paise wire contract stays separate from the ORM and domain |

## How to run and verify

```
make setup          # uv sync + pre-commit install (needs uv and Docker)
make check          # ruff, mypy --strict, pytest incl. PostgreSQL integration, coverage gates
make dev            # http://127.0.0.1:8000/health
curl 'http://127.0.0.1:8000/api/v1/offers?priceInPaise=2200000&productId=P1&brandId=B1&categoryId=C1'
curl -X POST http://127.0.0.1:8000/api/v1/payment-links -H 'Idempotency-Key: demo-key-0001' \
     -H 'Content-Type: application/json' \
     -d '{"offerId":"mock-offer-card-6m","priceInPaise":2200000,"productId":"P1","brandId":"B1","categoryId":"C1"}'
make openapi        # regenerates backend/openapi.json (a test fails if the committed copy drifts)
```

MR diff commands (no remote yet, ADR 0008):

```
git diff --stat main...HEAD
git diff main...HEAD > layer-1.diff
git log --oneline main..HEAD
```

## Test and coverage results

`make check` exits 0 at HEAD (2309af2):

| Check | Result |
|---|---|
| ruff check, ruff format | Clean |
| mypy --strict | Clean |
| detect-secrets | Baseline clean |
| pytest | **1,242 passed** (1,135 unit, 23 contract, 84 integration against Compose PostgreSQL) |

The contract suite runs every port test against both the Mock and the Paytm adapter (fed by fixtures).

| Coverage gate | Required | Actual |
|---|---|---|
| Overall | 85% | 100% |
| `domain/` | 100% | 100% |
| `core/` | 100% | 100% |
| `events/audit_subscriber.py` | 100% | 100% |
| `repositories/audit_event_repository.py` | 100% | 100% |
| `services/` | 90% | 100% |
| `adapters/` | 90% | 100% |

Acceptance criteria from IMPLEMENTATION_PLAN.md §8.1, with the criterion restated per ADR 0001: all met (reviewer agent verdict **Ready**, no blocking issues).
- Plan A is 5 × 366,667 + 366,665 paise; plans B and C are 6 × 385,000 and 12 × 205,000; extras are 0, 110,000 and 260,000.
- A create-link timeout gives 504 with one gateway call, and the replay gives 409.
- A bad webhook signature gives 401 plus an audit row.
- A repeated webhook has no extra effect.
- OpenAPI is valid and in sync.

## What to review first

1. `services/payment_handoff_service.py`, `services/create_link_outcome.py` and `domain/payments/payment_attempt_transitions.py`: the idempotency flow, the two-transaction create, and the guard that never overwrites a status a webhook reported mid-call.
2. `adapters/payment_gateway/paytm_error_translator.py` and `core/resilient_http_client.py`: outcome-unknown vs failed vs rejected, and proof that create is never retried.
3. `adapters/payment_gateway/paytm_adapter.py` (`verify_webhook`), `checksum_signer.py` and `api/controllers/paytm_webhook_controller.py`: the signature is checked before any field is read.
4. `adapters/payment_gateway/paytm_api_definitions.py`: every [Verify] item.
5. `domain/money.py`, `domain/emi/emi_schedule.py` and `tests/unit/domain/emi/test_emi_reference_table.py`: the paise maths behind the acceptance figures.

### Reading the MR (size)

About 19,700 changed lines, excluding `uv.lock`, `openapi.json` and `.secrets.baseline`. That is about 13 times the ~1,500-line guideline; roughly 57% is tests. Read it as six commit groups, and read `src/` first in each:

| Group | Commits | Size |
|---|---|---|
| A Foundation | d9d3dea, 6ca30f2, 7fd3aae | ~1.2k |
| B Domain maths | 7def08a, ef4e96e, 1533f66 | ~1.5k |
| C Persistence | 289cec5 | ~2.1k |
| D Port, Mock, resilience | 8ae9221, 870d1e5, 69d3326 | ~4.1k |
| E Paytm adapter | 5ae3018, 5d7666a, 228db91, 59aba55 | ~4.4k |
| F Factory, services, API | e41567a, e324e5a, 9858dcc, adf8a56, 2309af2 (reviewer fix) | ~6.8k |

In group E, read 5d7666a and 59aba55 as a pair: the latter replaces the 501/502 rule.

Functions over the 30-line soft limit, with justification:
- `payment_link_controller.create_payment_link` (35 lines) is mostly `Annotated` parameter declarations.
- `payment_status_service._apply_report` (34 lines) is mostly event keyword arguments.
- Migration 0001's `_create_payment_attempt_table` (32 to 37 lines) is a single `op.create_table` call.
- A handful of test builders and fixtures.

## Known limitations and mocks

- **The Mock gateway is the default.** No Paytm credentials exist. The Paytm adapter is tested only against documented-shape fixtures written from the public docs (ADR 0007), never against a live account.
- **Mock plan C** ("Demo cardless lender (Mock)") has no Paytm equivalent. Banks/Tenures cover card EMI only.
- **Production Paytm hosts are not documented** and have no default.
- **No auth or rate limiting yet** (ADR 0009). The status endpoint calls the gateway on every request.
- **Settlement data / SettlementPort** is deferred to Layer 2 (ADR 0006).
- **`ReducingBalanceStrategy` has no production caller yet.** It is kept for rate-quoted offers and cross-checks.

### [Verify] items to confirm once Paytm staging keys exist

All live in `adapters/payment_gateway/paytm_api_definitions.py`.

1. Staging hosts `securestage.paytmpayments.com` (Banks, Tenures, Create Link) and `securegw-stage.paytmpayments.in` (v3 status); production hosts.
2. Paths `/theia/api/v1/emiSubvention/banks`, `/theia/api/v1/emiSubvention/tenures` (both with `?mid=`), `/link/create`, `/v3/order/status`.
3. The `{head, body}` envelope for requests and replies.
4. Banks/Tenures head: `requestId`, `requestTimestamp`, `version` v1, `tokenType` CHECKSUM, `token` over the exact body text.
5. Item shape: `id`/`productId`, `brandId`, `categoryList`, `price` (rupees, two decimals), `quantity` 1. `model`, `ean` and `originalPrice` are omitted.
6. Tenures `filters` {`bankCode`, `cardType`}.
7. Banks reply nesting: `emiTypes[].cardTypes[]` and `bankDetails`.
8. Tenures reply: `planDetails[]` {`planId` (assumed unique), `emiType`, `interval`, `emi`, `interest`, `gratifications`}; `bankName` used as the lender label.
9. Net extra = `interest` − gratification (DISCOUNT and CASHBACK). This assumes `interest` is gross (ADR 0010).
10. Banks/Tenures `resultStatus` S/F. No failure codes are documented, so every F maps to INVALID_REQUEST.
11. Create Link head `tokenType` AES and `signature`.
12. Create Link body:
    - `linkType` FIXED, `amount`, `linkOrderId` = our order id, `statusCallbackUrl`.
    - `simplifiedSubvention` {`customerId`, `items`, `selectPlanOnCashierPage`}.
    - `partialPayment`, `bindLinkIdMobile` and contact fields are omitted.
    - The `linkName`/`linkDescription` text is English only for now.
13. Create Link reply: `linkId`, `shortUrl`. Result-code mapping includes 501/502 as rejected (ADR 0011).
14. v3 status request {`mid`, `orderId`}, head `signature`.
15. v3 status reply:
    - The reply head signature is checked over the raw body text.
    - Status mapping: TXN_SUCCESS→PAID, TXN_FAILURE→FAILED, PENDING, NO_RECORD_FOUND→NOT_FOUND.
    - 334/335/501 are handled as errors (ADR 0011).
16. Our order id = `linkOrderId` = v3 `orderId` = webhook `ORDERID`.
17. Webhook:
    - Form-urlencoded POST.
    - `CHECKSUMHASH` covers all other sorted fields, with "null" signed as empty.
    - `MID` must match ours; `STATUS` vocabulary.
    - `PAYMENTEMAILID` and `PAYMENTMOBILENUMBER` are never read.
18. Checksum algorithm: IV, 4-character salt, sha256 + salt, AES-CBC, base64. Our known-answer vector is self-generated.

## Open questions for the next layer

1. **Snapshot when the lender's quote mismatches.** `GET /offers` shows the lender's monthly figure (ADR 0001). The stored `OfferSnapshot` and the `lastInstallmentInPaise`/`totalPayableInPaise` fields come from our schedule. On a mismatched offer, (n−1) × monthly + last ≠ total. Layer 3's consent snapshot must store exactly what was shown: decide which figure is authoritative there. Also unify `monthlyInstallmentInPaise` (offers) and `regularInstallmentInPaise` (snapshot).
2. **Stuck LINK_CREATION_IN_PROGRESS.** If the process crashes between the two create transactions, the attempt stays in progress and replays get 409 until a gateway report arrives. Since the reviewer fix (2309af2), a late PAID, PENDING or FAILED report is recorded and audited. Decide on a time-based recovery (for example, treat it as OUTCOME_UNKNOWN after the gateway timeouts).
3. **Shared breaker and discovery latency.** Discovery reads and Create Link share one breaker per host, and create-link re-runs full discovery first. Consider an overall deadline or separate breakers.
4. **PAID report on a LINK_CREATION_FAILED attempt is ignored.** ADR 0011 decision 2 accepts that Paytm may have made a link despite Create Link body codes 501/502. If a customer pays on such a link, the PAID report is not recorded. Decide whether LINK_CREATION_FAILED should accept PAID.
5. **Paytm field names in webhook OpenAPI examples** (`paytm_webhook_controller.py`). Move them to a generic example, or accept them in an ADR. Also extend the vendor-term architecture test beyond `domain/` and `port.py`.
6. **Rate limiting** for the status and webhook endpoints, together with Layer 2 auth.
7. **The customer-facing link description** is English only; Tamil comes in Layer 3.
8. **`make check` per commit:** it ran green before each commit, including pre-commit hooks. The reviewer independently re-ran it at HEAD only.

## Next layer prerequisites

- Merge this MR to `main`. Layer 2 starts a new branch `layer/2-merchant-ui` from `main`.
- Layer 2 adds:
  - merchant pairing and auth;
  - the `sale` aggregate with `SaleStateMachine`, linking `payment_attempt` through a new `sale_id` column and migration (ADR 0009);
  - the merchant endpoints;
  - SettlementPort with its Mock (ADR 0006);
  - the live status feed as a second event-bus subscriber.
- The frontend generates its API client from `backend/openapi.json` (`make openapi`).
