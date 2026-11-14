# LAYER-3-WIP: Phase 3A (customer contract, comfort engine, ranking and alternatives)

Work in progress. Layer 3 runs in parallel with Layer 2 (ADR 0012). This file replaces a handoff until the Layer 3 gate, where it becomes `LAYER-3-HANDOFF.md`. Branch `layer/3-customer-ui`, worktree `../emi-copilot-l3`. Phase 3A is done. Next come sync point 1 (rebase onto Layer 2 step 2.5) and then Phase 3B.

## Built (files and endpoints or screens)

| Piece | Where (under `backend/src/emi_copilot/`) |
|---|---|
| 3.2 Comfort engine | `domain/comfort/` holds `ComfortRatio`, `ComfortBand` (exactly three bands), `ComfortThresholds` / `DEMO_COMFORT_THRESHOLDS` (35% and 50%, labelled demo heuristics [Verify]), `ComfortBandClassificationStrategy`, `FinancialProfile` and `assess_comfort`. `adapters/financial_profile/` holds `FinancialProfilePort` and `MockSyntheticFinancialProfileAdapter` (standard and risky profiles; it logs a warning when built). |
| 3.3 Ranking | `domain/ranking/` holds `PlanRankingStrategy`, `BudgetFit`, `RankedPlan` / `PlanRanking`, `PlanReasonCode` (facts only) and `calculate_monthly_commitment`. |
| 3.3 Alternatives | `domain/alternatives/` holds `DownPaymentRule`, `PlanAlternativeFinder`, `PlanAlternative(s)`, `CheaperModelQuote` and `AlternativeKind`. |
| Plan advice | `services/plan_advice_service.py` and `plan_advice_types.py`. These are the real services, reused in 3C. They depend on a `PricedOfferSource` protocol that Layer 1's `OfferDiscoveryService` satisfies. |
| 3.0 Stub flow | `services/customer_flow/` holds the DESIGN_SPEC §4 sample, an in-memory store with one store per app instance, the session, advice and consent services, and a selection quoter. Every class is marked STUB until 3C. |
| 3.0 Contract | DTOs `dtos/customer_*`, `comfort_check_dtos.py` and `plan_alternative_dtos.py`. Controllers `api/controllers/customer_*`. Contract app `api/customer_contract_application.py`, which is **not mounted in `main.py`**. Export with `make openapi-customer` to `backend/openapi.customer.json`. |

Endpoints (all under `/api/v1`, served only by the contract app). Every endpoint except the first needs the `X-Customer-Session-Token` header.

| Method and path | Purpose |
|---|---|
| `POST /customer-sessions` | Exchange a QR token for a session. Answers 201 with `Location` |
| `GET /customer-sessions/{id}` | Session summary (C1) |
| `PUT .../budget` | Confirmed monthly budget (C2) |
| `POST .../comfort-check` | Consented comfort check, or skip it (C3) |
| `GET .../plans` | Ranked plans, with reason codes and an optional comfort result per plan (C4, C5) |
| `POST .../alternatives` | Down payment, longer tenure and cheaper model, each recomputed by the engine (C6) |
| `POST .../consent/otp` | Request an OTP (C9). Returns the last two digits of the phone and the expiry |
| `POST .../consent` | `Idempotency-Key` required. Records the exact selection and the figures shown. Answers 201 with `Location` (C9) |
| `GET .../receipt` | Receipt in the `READY_TO_PAY` handoff state. It has no payment URL, because the merchant pays on Paytm (C10) |

The commits, in order, are below. `make check` passed before every one.

```
1007675 docs(rules): add ADR 0020 for Layer 3 Phase 3A decisions
973788e feat(domain): add comfort ratio, band classification and synthetic profile port
62c50a8 feat(domain): add plan ranking strategy with reason codes
0cb7adb feat(domain): add smarter alternatives recomputed by the EMI engine
6b73884 feat(api): add plan advice service
37a099d feat(api): add stub customer flow services
edb0511 feat(api): add customer API contract with unmounted stub controllers
9ab04da build(api): export the customer OpenAPI contract with make openapi-customer
78ee97f fix(domain): derive the down payment from the plan's total payable
2ebfdcd fix(api): let consent record the exact plan shown, including C6 alternatives
e96d8ed fix(api): keep consent evidence on a new scan and stop session probing
019facc docs(rules): add ADR 0021 for consent selection and session re-scan
```

The engines were built before the contract. The owner's order was 3.0 first. The order changed so that the stub responses are computed by the real engines instead of being typed in by hand, which keeps the documented numbers from drifting. A test replays a full stub run and requires the OpenAPI examples to match it exactly.

## Why (decisions, with ADR links)

- [ADR 0012](../adr/0012-parallel-layer-3.md): parallel work. No migrations. Routers are not mounted until 3C. Layer 3 ADRs start at 0020.
- [ADR 0020](../adr/0020-layer-3-comfort-ranking-and-alternatives.md): the comfort, ranking and alternatives rules.
  - **The engine wins over the C6 mockup** (owner decision): a ₹4,000 down payment gives **₹3,000 a month at 36.7%**, not ₹2,999 at 36.6%. Never copy the mockup figure into fixtures.
  - The down payment is derived as the chosen plan's total payable minus budget × tenure, rounded up to the next ₹1,000 (owner decision).
  - Budget fit and the comfort ratio use the largest single installment.
  - The band comes from the rounded basis points, so the % shown and the band always agree. 35.00% and 50.00% are Stretching.
  - Ranking puts within-budget plans first, then sorts by amount above budget, then extra, then tenure, then offer id. No plan is ever dropped.
- [ADR 0021](../adr/0021-customer-consent-selection-and-session-rescan.md): consent names the exact selection (offer, down payment, product) and the figures shown. A changed figure gives 409 `SHOWN_PLAN_CHANGED`. Re-scanning the QR keeps the consent evidence. Session probing gets one answer. The OTP is left out of the idempotency fingerprint. **The status is "orchestrator decision; owner to confirm".**

## Patterns used (pattern, file, problem solved)

| Pattern | File | Problem solved |
|---|---|---|
| Value Object | `domain/comfort/comfort_ratio.py`, `domain/ranking/budget_fit.py`, `domain/alternatives/plan_alternative.py` | Exact maths with one rounding step; invalid states cannot be built |
| Strategy (concrete, injected configuration) | `comfort_band_classification_strategy.py`, `plan_ranking_strategy.py` | Threshold and ordering rules are swappable and tested on their own. There is no abstract base while only one rule exists |
| Port and Adapter + Mock | `adapters/financial_profile/` | Synthetic profiles today; a real account-aggregator adapter can replace them later |
| DTO | `dtos/customer_*` | Keeps the wire contract (camelCase, paise, basis points) apart from the domain |
| Temporary composition root | `api/customer_contract_application.py` | Serves and exports the contract without touching `main.py` or `dependencies.py` while Layer 2 edits them |

## How to run and verify (exact commands)

```bash
cd ../emi-copilot-l3
make check                 # ruff, mypy strict, pytest with coverage gates
make openapi-customer      # rewrites backend/openapi.customer.json; git diff must be empty
make openapi               # backend/openapi.json must stay byte-identical (main app untouched)
```

This worktree has a **git-ignored `.env`** (`COMPOSE_PROJECT_NAME=emi-copilot-l3`, Postgres on port 55433, `BACKEND_PORT=8001`). Without it, both worktrees share one Postgres container and one test database. If the worktree is recreated, recreate that file.

Design numbers covered by tests (several of them end to end through HTTP):

- **Comfort ratios:** A 3,889 bp, B 3,950 bp, C 3,350 bp; Risky (₹20,000 inflow, plan B) 5,925 bp.
- **Ranking at a ₹3,000 budget:** cardless, then no-cost (66,667 paise above), then card (85,000 above).
- **No plan fits (₹1,800 budget):** all three plans are listed, each marked above budget.
- **Alternatives:** ₹4,000 down gives 300,000 paise a month at 3,667 bp; longer tenure (cardless 12 months) is 3,350 bp; the 64 GB model at ₹18,000 gives 300,000 paise at 3,667 bp.

## Test and coverage results

- 1,608 tests pass: 287 new ones on top of Layer 1's 1,321.
- Coverage is 100% line and branch, overall and on every gate (domain, core, services, adapters).
- Ruff and `mypy --strict` are clean.
- A reviewer agent found 1 blocking issue and 4 should-fix issues. All were fixed in `78ee97f`..`e96d8ed`, and the remaining notes are listed below.

**MR size:** Phase 3A adds about 3,800 source lines and 3,100 test lines (plus the generated `openapi.customer.json`). That is above the roughly 1,500-line guide in git-workflow.md §4. Review it in commit groups:

1. ADR 0020 and the domain engines.
2. The plan advice service.
3. The stub flow and the contract.
4. The review fixes and ADR 0021.

## Known limitations and mocks

- **Everything under `services/customer_flow/` is a STUB**, and so is the contract app:
  - in-memory state;
  - two fixed sample QR tokens (standard and risky profile);
  - a fixed OTP;
  - the Mock gateway priced without the offer-mismatch audit (`StubGatewayPricedOfferSource`).
- The financial profiles are synthetic (`MockSyntheticFinancialProfileAdapter`). The comfort check is advice, not a credit decision.
- The cooling-off wording is `PLACEHOLDER` until the lender confirms the period.
- OTP verify and consent have no rate limit or attempt limit yet (security-and-compliance.md §4). This is required in 3C.
- A re-scan gives a new token with a fresh 30-minute lifetime.
- `previousMonthlyInstallmentInPaise` is the lender's quoted figure, while `isLowerMonthlyAmount` compares the largest installments. They can disagree only when a plan's last installment is larger than its regular one. This is documented in the DTO.
- On customer endpoints the OpenAPI document leaves out the `PAYMENT_GATEWAY_REQUEST_REJECTED` example, because the shared example text contains a banned word. The API can still return that code.

## Open questions for the next phase

1. **Consenting to an alternative changes the sale** (ADR 0021). A cheaper model or a down payment changes what the merchant collects, and Layer 2 owns the sale. How does the merchant see and collect a down payment or a model swap?
2. **Plan names.** "No-cost EMI", "Card EMI" and "Cardless credit", and the "Brand-funded" / "On your card" lines (C4), cannot be derived from `emiType` or `lenderLabel`. Is a `planKind` field needed, and where does it come from?
3. **Phone number source.** C9 shows "ending 42", but no screen collects a phone number. Does it come from the merchant's sale (Layer 2)?
4. **"2 tries left" (C9).** This needs a remaining-attempts value, and the shared problem body has no extension field for it.
5. **Client generation in 3B.** Layer 2's generator reads `backend/openapi.json` only. Should 3B point it at `openapi.customer.json` as well, or generate a second client until 3C merges the two?
6. Confirm the ADR 0020 defaults: the largest installment, the band from the rounded basis points, and the tie-break order.
7. Confirm ADR 0021.

## Next phase prerequisites

- **Sync point 1:** Layer 2 commits step 2.5 (workspace, `ui-kit`, `api-client`, i18n). Then rebase this branch onto it (PARALLEL_LAYER_3.md §4.2). The existing files this branch edits, all additively, are where conflicts are likely:
  - `domain/errors.py`
  - `api/error_handlers.py`
  - `tests/unit/api/test_error_handlers.py`
  - `tests/unit/architecture/test_services_import_boundaries.py`
  - `Makefile`
- **Phase 3B:** the customer UI against a fixture API, using `openapi.customer.json` as the type source.
- **Phase 3C, after the Layer 2 merge:**
  - Mount `CUSTOMER_ROUTERS` in `main.py` and fold the contract-app wiring into `api/dependencies.py`.
  - Delete `openapi.customer.json` and the contract app.
  - Narrow Layer 1's "unauthenticated" OpenAPI test to the gateway routes.
  - Replace the stubs with repositories, one migration chain and `OfferDiscoveryService`.
  - Add rate limits, and the merchant-privacy cross-layer test.
