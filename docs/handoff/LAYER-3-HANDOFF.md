# LAYER-3-HANDOFF: Customer UI + customer backend slice

Branch `layer/3-customer-ui`, rebased on the Layer 2 tip `71d9a22` (Layer 2 gate). Not pushed. Replaces `LAYER-3-WIP.md`. Layer 3 ran in parallel with Layer 2 (ADR 0012): Phase 3A (engines and stub contract) before the Layer 2 merge, then Phases 3B and 3C together. The customer app was built in a second worktree in parallel with the backend and cherry-picked in.

## What was built

**Customer journey (phone, opened by the merchant's QR):** C1 welcome and language, C2 budget, C3 comfort-check consent or skip, C4 ranked plans, C5 comfort detail, C6 smarter alternatives, C7 plain-language explanation (template text), C9 consent with OTP, C10 hand-off and receipt. English and Tamil (Tamil marked draft). C8 teach-back, the C2 microphone and C7 audio are Layer 4 (ADR 0022 decision 7).

**Backend (`backend/src/emi_copilot/`):**

| Piece | Where |
|---|---|
| Comfort engine (3 bands, 35% / 50% demo heuristics) | `domain/comfort/`, `adapters/financial_profile/` (Mock synthetic profiles) |
| Ranking with factual reason codes; never hides a plan | `domain/ranking/` |
| Alternatives: down payment, longer tenure, cheaper model, all recomputed by the EMI engine | `domain/alternatives/` |
| Customer session, OTP challenge, hash-chained consent record | `domain/customer_sessions/`, `domain/consent/` |
| Migration 0006: `customer_session`, `consent_otp_challenge`, `consent_record` (append-only trigger, unique previous hash, one consent per sale) | `alembic/versions/0006_*` |
| Mock Paytm contact source (phone ending 42) and Mock OTP sender | `adapters/customer_contact/`, `adapters/consent_otp/` |
| Services: session (single-use QR exchange), choices (budget, comfort), plans and alternatives, OTP, consent, receipt, explanation | `services/customer/` |
| Shared in-transaction "agree the plan" step used by consent and Layer 2's `MarkSaleReadyToPayService` | `services/sale_agreement_step.py` |
| Template explanation (EN, TA draft); Layer 4 wraps it | `services/customer/template_explanation_service.py` |
| Controllers, DTOs, rate limits, composition root | `api/controllers/customer_*`, `dtos/customer_*`, `api/rate_limiting.py`, `api/customer_dependencies.py` |

**Endpoints** (`/api/v1`, header `X-Customer-Session-Token` except the first): `POST /customer-sessions` (QR exchange, 201 + Location), `GET /customer-sessions/{id}`, `PUT …/budget`, `POST …/comfort-check`, `GET …/plans`, `POST …/alternatives`, `POST …/explanation`, `POST …/consent/otp`, `POST …/consent` (Idempotency-Key, 201 + Location), `GET …/receipt`.

**Frontend (`frontend/`):** `apps/customer-web` (flow reducer with typed steps, features per screen, `CustomerFlowApi` port with HTTP and fixture adapters), additive `ui-kit` `BandChip`, additive `shared-i18n` band labels, additive api-client customer session-token option, Playwright customer specs in `e2e/`.

## Why (decisions)

- [ADR 0012](../adr/0012-parallel-layer-3.md) parallel work; [ADR 0020](../adr/0020-layer-3-comfort-ranking-and-alternatives.md) comfort, ranking, alternatives (engine wins over the C6 mockup: ₹3,000 a month at 36.7%); [ADR 0021](../adr/0021-customer-consent-selection-and-session-rescan.md) probing and idempotency rules (decisions 1 to 3 superseded); [ADR 0022](../adr/0022-layer-3-customer-integration.md) integration.
- Owner decisions: down payment derived from the budget; C6 down payment and cheaper model are "ask the shop" (not consentable here); phone number from the payment side (Mock Paytm source, real one [Verify with Paytm]); OTP tries left at the orchestrator's choice (3 tries, 5 minutes, 30 s resend wait).
- The QR exchange is single-use (rule files win over ADR 0021 decision 3).

## Patterns used

| Pattern | File | Problem solved |
|---|---|---|
| Strategy | `domain/comfort/comfort_band_classification_strategy.py`, `domain/ranking/plan_ranking_strategy.py` | Threshold and ordering rules swappable and tested alone |
| Value Object | `domain/comfort/comfort_ratio.py`, `domain/consent/` | Exact maths, one rounding step, invalid states impossible |
| Port and Adapter + Mock + Factory | `adapters/financial_profile/`, `adapters/customer_contact/`, `adapters/consent_otp/` | Synthetic data and mock delivery today, real sources later |
| Repository + Unit of Work | `repositories/customer_session_repository.py`, `consent_record_repository.py`, `services/sale_agreement_step.py` | Consent row and sale agreement commit together or not at all |
| Observer | `CustomerBudgetConfirmed`, `CustomerPlansViewed`, `ConsentRecorded` events; `events/funnel_event_recorder.py` | Funnel and audit without coupling services |
| Template fallback | `services/customer/template_explanation_service.py` | Always a safe explanation; Layer 4 decorates it |
| Finite state machine (UI) | `apps/customer-web/src/features/customer-flow/model/` | Consent unreachable without a confirmed budget and a chosen plan |
| Container / Presentational, Adapter + Factory (UI) | `apps/customer-web/src/features/*`, `features/customer-flow/api/` | Data and flow logic apart from rendering; fixture API for tests |

## How to run and verify

```bash
cd ../emi-copilot-l3           # needs the git-ignored .env (own Postgres on 55433, backend 8001)
make check                     # backend + frontend gates
make openapi-check             # openapi.json and the generated client in sync
make e2e E2E_BACKEND_PORT=8011 E2E_MERCHANT_WEB_PORT=5182 E2E_CUSTOMER_WEB_PORT=5183
```

Manual demo: `make migrate seed`, run the backend on 8001, merchant-web pointed at 8001, customer-web on 5174 (`pnpm --filter @emi-copilot/customer-web dev`). Start a sale on M2, open the QR link on a phone-sized window. Mock OTP: `123456` (setting `MOCK_CONSENT_OTP_CODE`).

## What to review first

1. `backend/src/emi_copilot/services/customer/customer_consent_service.py`: OTP check, shown-figure check, then one unit of work for the consent row and READY_TO_PAY (lock order: chain, sale, OTP challenge).
2. `backend/src/emi_copilot/domain/consent/consent_record_hasher.py` and `repositories/consent_record_repository.py`: canonical JSON, genesis hash, advisory lock, fork prevention.
3. `backend/src/emi_copilot/services/customer/customer_session_service.py` (`start`): single-use QR exchange with one answer for every refusal.
4. `backend/tests/integration/api/customer/test_merchant_privacy_after_customer_flow.py`: the cross-layer privacy test (CLAUDE.md rule 6).
5. `frontend/apps/customer-web/src/features/customer-flow/model/` (flow reducer) and `features/consent/hooks/useConsentWithOtp.ts`.

**MR size:** about 14,900 source lines and 9,000 test lines on top of Layer 2 (excluding the lockfile, `openapi.json` and the generated client), far above the ~1,500-line guide (git-workflow.md §4). Review it in commit groups:
- A. Phase 3A engines: `fc9be93`..`1e209f4` (ADR 0020/0021, comfort, ranking, alternatives, plan advice; the stub contract commits in this range are removed again in B).
- B. Customer backend: `0e22a9e`..`c16eb87` (ADR 0022, domain, migration 0006, adapters, services, mount, end-to-end and privacy tests).
- C. Customer app: `33eb814`..`1089444` (ui-kit addition, customer-web, generated client switch, Playwright).
- D. Gate fixes and documents (the last commits).

**Over the soft limits (CLAUDE.md §7), with reasons:**
- `domain/errors.py` (483 lines) and `api/error_handlers.py` (332): one class / one mapping row per error code across all layers; splitting by area is a follow-up.
- `repositories/unit_of_work_protocol.py` (318): one protocol per repository, kept together as the unit-of-work contract.
- `api/dependencies.py::build_application_components` (67 lines): the composition root builds every component in one place (ADR 0008).
- `plan_advice_service.suggest_alternatives` (39), `customer_session_service._open_session` (36), `consent_otp_service.request_otp` (34), `customer_consent_service._record_consent` (31): each is one transaction whose steps read best in order; three migration 0006 helpers are table definitions.

## Test and coverage results

- Backend: 2,967 tests pass (Layer 2 left 2,591; Layer 3 added about 376). Coverage is 100% line and branch overall and on every gate (domain, core, services, adapters).
- Frontend: 489 Vitest tests in 66 files pass with axe on every screen; coverage about 98% lines, 94% branches; the customer flow reducer is at 100%.
- ruff, `mypy --strict`, detect-secrets: clean. `make openapi-check`: in sync.
- Playwright (`make e2e`): 8 of 8 pass in about 27 s (4 merchant, 4 customer: English path with M3 "Ready to pay" live, Tamil path, skip comfort, reused QR).
- Customer bundle: one main chunk of 95.5 KB gzipped (budget 150 KB); the fixture API is a separate 3 KB chunk the real flow never loads.
- Review at the gate: the reviewer found no code blockers. Four should-fix items were fixed (`104dbf1`..`872fae3`): paytm mode refuses the mock OTP and phone sources; `MOCK_FINANCIAL_PROFILE=risky` makes the Risky demo reachable; PLANS_VIEWED is recorded only while the sale is CHOOSING; the fixture API left the production bundle. The fixture has its own entry file `features/customer-flow/fixture.ts` so it can be loaded lazily (a small bend of frontend.md §2).

## Known limitations and mocks

- Financial profiles are synthetic (Mock); `MOCK_FINANCIAL_PROFILE=standard|risky` picks the profile for the demo (standard is ₹30,000 inflow, risky ₹20,000). The comfort check is advice, not a credit decision; thresholds are demo heuristics [Verify].
- The phone number comes from `MockPaytmCustomerContactAdapter`; the OTP is a fixed demo code sent by a Mock. Real sources [Verify with Paytm].
- Down payment and cheaper model cannot be consented on the phone; the merchant starts a new sale for another model, and a counter down payment is not supported in this build.
- Cooling-off wording is a placeholder until the lender confirms the period.
- Reloading the customer page needs a new QR from the shop (session token kept in memory only).
- C5's 35% / 50% marks and "how we read this" lines are fixed text; they must change with the thresholds.
- Tamil strings are drafts until a native speaker reviews them (Q13).
- Rate limiters are in-memory per process (as in Layer 2); one uvicorn worker.
- The consent reference is a display label, not unique; the consent id identifies a record.

## Not done / follow-ups

- Split `domain/errors.py` and `api/error_handlers.py` by area.
- Return the comfort thresholds from the API so C5's marks follow `DEMO_COMFORT_THRESHOLDS`.
- Consent reference: a random 4-digit serial without a year can repeat; make it unique (or add the year and a longer serial) before support uses it for lookups.
- M5 budget buckets with a single sale in the range reveal that customer's budget band; consider a minimum count (Layer 2 report rules).
- Choose-language endpoint: `CustomerChoiceService.choose_language` exists but C1's choice is sent per request (Accept-Language), not stored on the session.
- Rate limiters are per process and keyed by address and session; move to a shared store before more than one worker.
- Remove the parallel worktree `../emi-copilot-l3-web` (branch `layer/3-customer-web`) after this MR is accepted.

## Open questions

1. Confirm ADR 0022 decisions 4 to 9 (orchestrator decisions in the approved plan), especially the single-use QR (a reload needs a new QR from the shop).
2. Which Paytm API, if any, gives the customer's phone number for the consent OTP (ADR 0022 decision 2)? Until then paytm mode refuses to start with the mock consent sources.
3. Who reviews the Tamil strings (Q13)?
4. Should the merchant be able to set up the down payment or the cheaper model for the customer (ADR 0022 decision 1), in a later layer?

## Next layer prerequisites (Layer 4)

- Wrap `TemplateExplanationService` with an audited AI decorator (number audit against engine output; fall back to the template).
- Add speech endpoints for the C2 microphone, C7 audio and C8 teach-back.
- Accept-Language already selects the explanation language.
