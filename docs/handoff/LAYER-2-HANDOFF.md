# LAYER-2-HANDOFF: Merchant UI + merchant backend slice

Branch `layer/2-merchant-ui`, from `main` at 2f8baa0, 2026-11-15. This file doubles as the MR description (git-workflow.md §4).

## What was built

### Backend (`backend/src/emi_copilot/`)

**Pairing and auth (2.1):**
- `POST /merchants/pairing` exchanges shop ID and PIN for a 12-hour opaque token.
- The PIN is stored as an scrypt hash; the token only as SHA-256.
- 5 wrong PINs lock the shop for 15 minutes, and pairing is rate-limited per address.
- `GET /merchants/me` and `GET /products` (products carry their offer counts).
- The Mock gateway now quotes plans per product: 128 GB phone 3, 64 GB phone 2, earbuds 1.

**Sales (2.2):**
- `SaleStateMachine` with the five merchant-visible statuses and 60-minute expiry.
- The frozen `ChosenPlan`.
- Signed QR tokens (HMAC, 15 minutes, fragment-only URL, nonce hash stored).
- An append-only `funnel_event` table.
- `POST/GET /sales` and `/sales/{id}`, plus `POST /sales/{id}/qr-tokens`.

**Live status and payment handoff (2.3):**
- `GET /sales/events`, a server-sent events stream that is announced only after commit.
- M4 handoff: `GET /sales/{id}/handoff`, `POST .../payment-links` and `GET .../payment-status`.
- The Layer 1 payment endpoints now need the merchant token and are rate-limited.
- Stale link creation is recovered.
- `MockCustomerSimulator` (flag-gated, left out of OpenAPI) stands in for the customer until Layer 3.

**Reports (2.4):**
- Funnel, missed sales with budget buckets, suggested actions, money due and the weekly message (read and send).
- `SettlementPort` and `WeeklyMessageDeliveryPort`, each with a labelled Mock.
- Small-count suppression.
- The seeded week equals DESIGN_SPEC §4.

Migrations 0003–0005.

### Frontend (`frontend/`)

**Workspace (2.5):**
- pnpm workspace (sync point **93f2a5b** for the Layer 3 rebase).
- `ui-kit`: tokens, Tailwind theme and 11 components.
- `api-client`: generated from `backend/openapi.json`.
- `shared-i18n`: rupee formatting and EN/TA labels.
- An empty `customer-web` shell.

**merchant-web (2.6):**
- M1 pairing, M2 new EMI sale and counter list, M3 show QR (tablet and phone), M4 take payment, M5 sales report (the M6 and M7 panels open in place), M8 weekly message.
- Every screen is in English and draft Tamil.
- `useLiveSaleStatus` reads the stream with the `Authorization` header and falls back to polling.

**End to end (2.7):** `make e2e` runs Playwright against its own database and ports. It covers the tablet happy path, a Tamil pass and phone widths, with axe colour-contrast checks in Chromium.

### Endpoint summary (`/api/v1`; Bearer token except pairing)

| Method | Path | Purpose |
|---|---|---|
| POST | `/merchants/pairing` | Shop ID + PIN to token (rate-limited, lockout) |
| GET | `/merchants/me`, `/products` | Shop and device; products with plan counts |
| POST, GET | `/sales`, `/sales?view=counter`, `/sales/{saleId}` | Start a sale (returns the QR); today's counter list; one sale |
| GET | `/sales/events` | Live sale status (SSE) |
| POST | `/sales/{saleId}/qr-tokens` | Fresh QR while CHOOSING |
| GET, POST, GET | `/sales/{saleId}/handoff`, `/payment-links`, `/payment-status` | M4: EDC steps, payment link (Idempotency-Key), server-side status |
| GET | `/reports/funnel`, `/missed-sales`, `/suggested-actions` (`range=`) | M5 report |
| GET | `/reports/money-due`, `/reports/weekly-message` | Brand settlements (Mock); weekly message EN/TA |
| POST | `/reports/weekly-message/send` | Mark sent (Mock delivery, idempotent) |

`POST /payment-links` (Layer 1, no sale) is now deprecated (ADR 0014).

## Why (decisions, with ADR links)

| ADR | Decision |
|---|---|
| [0013](../adr/0013-merchant-pairing-tokens-and-rate-limits.md) | Seeded demo shop instead of an owner app; scrypt PIN, database lockout, hashed opaque token held in memory by the tablet; Layer 1 payment endpoints behind merchant auth |
| [0014](../adr/0014-sale-state-machine-chosen-plan-and-payment-links.md) | Five merchant-visible statuses (owner); tolerant payment outcomes; one payable link per sale, with recovery so a sale is never stuck; EDC is instructions only; bare `/payment-links` deprecated |
| [0015](../adr/0015-customer-qr-token.md) | HMAC QR token in the URL fragment; only the nonce hash is stored; session code is display only |
| [0016](../adr/0016-live-sale-status-stream.md) | SSE read with fetch and the header, broadcast after commit, single uvicorn worker |
| [0017](../adr/0017-mock-customer-simulator.md) | Labelled, flag-gated simulator for "agreed" and "paid" until Layer 3 |
| [0018](../adr/0018-reports-settlement-and-weekly-message.md) | Cohort funnel without open sales; IST periods; counts 1–4 suppressed (owner), including drops and derived fields; missed-sale rule; settlement Mock; backend-rendered template message (documented exception to backend.md §5) |
| [0019](../adr/0019-frontend-workspace-api-client-and-e2e.md) | pnpm workspace, tokens-only Tailwind, generated client with drift check, isolated e2e |

**Rule change made at the plan gate (owner):** CLAUDE.md rule 6 now lists PAID, PAYMENT_NOT_COMPLETED and EXPIRED as merchant-visible, and requires counts from 1 to 4 to be suppressed (commit da1d3d5).

ADR numbers 0013–0019 come from Layer 3's ADR 0012. Layer 3 owns 0012 and 0020 onwards.

## Patterns used

| Pattern | File | Problem solved |
|---|---|---|
| State | `domain/sales/sale_state_machine.py` | Only legal sale moves; repeated and late payment reports are safe |
| Observer | `events/funnel_event_recorder.py`, `sale_payment_outcome_subscriber.py`, `sale_status_broadcaster.py` | Funnel, sale status and the live feed react without coupling services |
| Unit of Work + after-commit | `repositories/unit_of_work.py`, `after_commit_callbacks.py` | Nothing is broadcast or delivered before commit |
| Port + Adapter + Factory | `adapters/settlement/`, `adapters/weekly_message_delivery/` | Settlement and sending are labelled Mocks, swappable later |
| Strategy | `domain/reports/suggested_actions.py` | Each suggestion rule is independent and tested on its own |
| Value Object | `ChosenPlan`, `ReportedCount`, `ReportingPeriod`, `SessionCode` | Frozen plan evidence; suppression and time-zone maths in one place |
| Repository | merchant, device pairing, product, sale, funnel, report query, weekly message | Scoped queries, no SQL in services |
| DTO | `dtos/merchant_*`, `sale_*`, `report_*` | Exact schemas that the privacy test pins |
| Container / Presentational; Adapter | `frontend/apps/merchant-web/src/features/*`, `packages/api-client` | No logic in components; generated types only |

## How to run and verify

```
make setup && make frontend-setup      # Python and pnpm dependencies, pre-commit hooks
make check                             # backend ruff, mypy, pytest and coverage gates; frontend tsc, ESLint, Prettier, Vitest and axe
make openapi-check                     # schema and generated client are in sync
make e2e-setup && make e2e             # Playwright; its own database emi_copilot_e2e, ports 8010 and 5180

# Demo: put DEMO_MERCHANT_PIN=<6 digits> in .env first
make db-reset && make demo             # migrate, seed this week, API on 127.0.0.1:8000 (1 worker, simulator on)
pnpm --dir frontend --filter @emi-copilot/merchant-web dev    # http://127.0.0.1:5173, pair with RAVI-0193 and the PIN
```

**Moving a sale on during the demo** (the token comes from `POST /api/v1/merchants/pairing`):
```
curl -X POST 127.0.0.1:8000/api/v1/mock-customer-simulator/sales/<saleId>/agreed-plan \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"offerId":"mock-offer-no-cost-6m"}'
curl -X POST 127.0.0.1:8000/api/v1/mock-customer-simulator/payments/<orderId>/completed -H "Authorization: Bearer $TOKEN"
```

**Proxy note:** the shell's `http_proxy` exempts `127.0.0.1` but not `localhost`, so use `127.0.0.1` URLs.

**MR diff commands:**
```
git fetch origin
git diff --stat origin/main...HEAD
git diff origin/main...HEAD > layer-2.diff
git log --oneline origin/main..HEAD
```

## Test and coverage results

Results of the orchestrator's own run at f3480ca, the last code commit.

| Check | Result |
|---|---|
| ruff, ruff format, mypy --strict, detect-secrets | Clean |
| pytest | 2,225 passed (unit, contract, integration on Compose PostgreSQL) |
| Backend coverage | 100% overall and on every gate (domain, core, services, adapters, audit) |
| tsc, ESLint (0 warnings), Prettier | Clean |
| Vitest + axe | 301 passed in 41 files; coverage about 98% lines (gate 80%) |
| `make openapi-check` | In sync |
| `make e2e` | 4/4 (tablet happy path, Tamil, M3 and M8 on phone); axe with colour contrast on every screen, 0 violations |

**Acceptance criteria (IMPLEMENTATION_PLAN §8.2):**
- M1–M5 and M8 match the mockups in layout, copy and states, in English and draft Tamil. Deliberate deviations are listed below.
- Merchant APIs never return income, EMIs, ratios or step history:
  - `tests/contract/test_merchant_response_privacy.py` pins exact fields, and a runtime check compares real responses with them.
  - The screens have a privacy test.
  - Reports exclude open sales and suppress small counts.
- Sale transitions follow the state machine, and expired QR tokens are rejected.
- Seeded report numbers equal the design: 120/96/88/51/44, drop 37, buckets 5/7/14/21/49, 12 missed under ₹3,000, ₹1,84,000 in 3 batches.
- `make check`, axe and the Playwright merchant path pass.

**Gate review:** the reviewer agent's verdict was "Ready after fixes", with two blocking findings:
- **B1:** a sale could be left with no way to get a payment link.
- **B2:** "Today" reports could follow one live customer.

Both were fixed. The re-review then found two remaining report leaks: a hidden drop still named its stage, and the budget total showed a hidden zero. Those were fixed together with complementary bucket suppression and two payment-link correctness items. The final checks below are from after those fixes.

## What to review first

1. `services/latest_sale_attempt_check.py` and `services/sale_payment_link_intent.py`: one payable link per sale, and recovery from stale or unknown attempts under the sale row lock.
2. `repositories/report_query_repository.py`, `domain/reports/small_count_suppression.py`, `funnel_report.py` (`report_drop`) and `missed_sales.py` (`without_suppressed_details`): the rule 6 protections in reports.
3. `events/sale_status_broadcaster.py` and `repositories/unit_of_work.py`: after-commit delivery and the thread to event-loop handoff.
4. `services/pair_device_service.py`, `core/pin_hasher.py`, `core/qr_token_signer.py` and `api/rate_limiting.py`.
5. `frontend/apps/merchant-web/src/features/live-sale-status/` and `shared/api/useIdempotencyKeyPerIntent.ts`.

### Reading the MR (size)

**Size:** 70 commits. About 37.7k changed lines excluding lockfiles, `openapi.json` and the generated client: about 11.6k in backend `src`, `alembic` and `scripts`, and about 7.9k in frontend source; the rest is tests. That is far above the ~1,500-line guideline, which the plan accepted (owner Q4: several commits per step, one MR read by commit groups).

**Commit groups:**

| Group | Commits |
|---|---|
| A Rules | da1d3d5 |
| B Pairing and catalogue | 1a99908 … e392234 |
| C Sales, QR, funnel, privacy test | 8caa5cd … 2a901f9 |
| D Live status, handoff, simulator | 097c9fc … 2803e77 |
| E Reports and seed | f3b01eb … 8d49fcd |
| F Frontend workspace | 0fc5fe4 … 93f2a5b |
| G Merchant screens | 6661bdd … 60cad11 |
| H End to end | f3df6ea … de24f1f |
| I Gate fixes, backend | 1293de0 … 7edf038 |
| I Gate fixes, frontend | 488e1cc … ae7a2cc |
| J Re-review fixes | 184f3bf … f3480ca |
| K Gate docs | the final docs commit |

**Already on `main`:** the owner asked for an early merge so Layer 3 could proceed, and `main` was fast-forwarded and pushed at ae7a2cc (groups A to I, every gate green). Groups J and K follow as a second fast-forward.

**Over the soft limits, with justification:**
- `api/dependencies.build_application_components` (46 lines): composition root wiring.
- `PaymentHandoffService` (244 lines): Layer 1 class plus the sale intent hook.
- `sale_controller.start_sale` (36) and `payment_link_controller.create_payment_link` (35): mostly `Annotated` parameters.
- `payment_status_service._apply_report` (34): from Layer 1.
- `domain/errors.py` (347 lines): the single typed-error module that the error-mapping test enumerates.
- Migrations 0004/0005 table builders and the demo seed writer: single `op.create_table` calls and seed data.
- Test files over 300 lines, kept whole so each screen or service reads as one specification: `test_sale_handoff_service.py`, `test_sale_handoff_endpoints.py`, `NewEmiSalePage.test.tsx`, `SalesReportPage.test.tsx`, `TakePaymentPage.test.tsx`.

## Deliberate differences from the mockups

**M1:**
- "owner app" became "Ask the shop owner for the pairing PIN".
- A wrong-PIN and a locked state were added (the spec lists them).

**M2:** no "Scan barcode"; the price at counter is read-only.

**M3:**
- No "Not scanned yet" state (rule 6).
- The QR is hidden after the customer agrees.
- The phone variant shows extra in total and total.

**M4:**
- Extra in total and total rows were added.
- The payment link is shown as a QR plus a copy button; nothing is sent.
- Amounts with paise show exactly (₹124.95), so the EDC amount is right.

**M5:**
- The summary's "Also sent to your phone every Monday" became a "Send to my phone" control (Mock delivery).
- The wording follows the numbers:
  - "The biggest drop was after seeing the plans", not "Most who left…".
  - The suggestion quotes ₹2,444 or ₹1,833 a month, not "near ₹3,000".
  - The panel says "the plan with the least extra adds ₹2,600", not "the only plan… so they walked away".
- The empty state ends "fills in as customers finish choosing".

**M8:** the "Listen" audio control is hidden until Layer 4.

**All screens:** spec sizes win: 48/56 px targets, money 32/700, tabular numerals.

## Not done / follow-ups

1. **Tamil:** all merchant Tamil strings are drafts and need native review (Q13).
2. **Retire or keep the bare `POST /payment-links`?** Scope payment idempotency keys per merchant (ADR 0014).
3. **PIN lockout:**
   - Anyone with a shop ID can lock that shop for 15 minutes.
   - Real shop IDs can be told from unknown ones.
   - The pairing limit is keyed by peer address, so all devices behind a proxy share it.

   All accepted for the demo (ADR 0013).
4. **Payment links before paytm mode:** add a margin or an overall deadline to the 26 s stale limit (ADR 0014).
5. **Report endpoints:**
   - The ones that call the gateway are not rate-limited.
   - One M5 load quotes each product about three times. Share or cache the quotes before paytm mode.
6. **Single uvicorn worker required** (in-memory rate limits and SSE fan-out). Use a shared broker before scaling.
7. **Demo drift:**
   - Seeded sale 4821 expires about an hour after seeding and then joins the reports (STARTED 121). Run `make db-reset && make demo` before a demo.
   - On a Monday the seeded history lands earlier the same day and shows on the counter list.
8. **Overdue CHOOSING sales** enter reports only once their expiry is recorded (next counter read or sale command).
9. **Money-due amounts on M5** show whole rupees (the batches are whole-rupee Mock data).
10. **No CI or remote pipeline yet:** `make openapi-check` and `make e2e` run locally.
11. **Merchant bundle size:** about 153 KB gzipped. The 150 KB budget applies only to the customer app.

## Open questions

1. Should `POST /api/v1/payment-links` (deprecated) be removed in Layer 3, and should payment idempotency keys be scoped per merchant?
2. Report only closed days? When one sale leaves CHOOSING, reloading M5 moves counts by one right after the counter list showed which sale changed. Suppression cannot hide a change of one in a large total (ADR 0018 residual risk).
3. Who reviews the Tamil strings before the demo?

## Next layer prerequisites

- Merge this MR to `main`. The Layer 3 worktree (`layer/3-customer-ui`, rebased on 93f2a5b) then rebases onto `main`.
- Layer 3 replaces the simulator's agree path with real consent through `MarkSaleReadyToPayService`, and fills `qr_token_exchanged_at`.
- Layer 3 writes BUDGET_TOLD and PLANS_VIEWED funnel events; the report suppression rules then apply to live data.
- Rebasing Layer 3 onto this branch: changes to `ui-kit`, `api-client` and `shared-i18n` after 93f2a5b are additive only:
  - `Chip` gains an `attention` tone.
  - `QrPanel` gains `stackedSize`.
  - The generated client changed with the OpenAPI.
