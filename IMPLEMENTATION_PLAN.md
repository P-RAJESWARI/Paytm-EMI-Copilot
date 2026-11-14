# IMPLEMENTATION_PLAN.md: Layer-by-layer build guide for Claude Code

**Project:** EMI-at-Counter Copilot (Team Thrivers_001)  
**Design source:** the "EMI Copilot – UI Mockups" canvas, copied to `docs/design/mockups-source/` and distilled into `docs/design/DESIGN_SPEC.md`  
**Status:** Q1 to Q3 answered by the owner (Python, no Paytm keys, Claude Code executes). Q4 to Q6 use the stated defaults unless the owner objects. **No code has been written yet.** The prompts to run each layer are in `PROMPTS.md`.  
**Labels:** **[Fact]** from a source, **[Inferred]** my reasoning or estimate, **[Verify]** confirm before relying on it.

---

## 1. Confirmation of understanding

| Item | My understanding |
|---|---|
| Goal | A production-quality, mentor-reviewable codebase that you can follow and learn from, built layer by layer, each layer ending in a clean MR and a written summary |
| Layer order | 1. Payment API connection, 2. Merchant UI, 3. Customer UI, 4. Sarvam AI integration |
| "Survam AI" | I read this as **Sarvam AI** (the speech and Indic-language provider whose credits you received). Tell me if you meant something else |
| Product | Paytm makes EMI available; we make it affordable and understood and show merchants why sales are lost. Merchant starts a sale, customer scans a QR, compares plans, optionally runs a consented comfort check, gets an explanation, consents with OTP, is handed off to Paytm to pay. Merchant sees a sales report |
| AI boundary | AI explains and transcribes only. It never calculates, approves credit, or triggers payment. Numbers pass a mandatory audit. Humans own every decision |
| Standards | Fully readable names, a one or two line purpose comment on every method, named design patterns, small single-responsibility files, clear layer folders |
| Process | Rule documents first, then layers. A summary and reviewable diff at the end of each layer. I pause at every layer boundary and ask before continuing. Ambiguities are raised, not guessed |
| Constraints from earlier work | LangGraph is approved. Sarvam credits provided. Pre-built code is allowed. Event is Sunday 15 Nov 2026 (today is Saturday 14 Nov) |

---

## 2. Questions and answers

> **Answered:** Q1 = Python. Q2 = no Paytm keys (Mock gateway is the default). Q3 = Claude Code executes. **Assumed defaults, change if wrong:** Q4 compressed plan for the event, Q5 yes, Layer 1 includes foundation, Q6 yes, LangGraph only in Layer 4.

**Blocking for Layer 1**

| # | Question | My default if you say "use defaults" |
|---|---|---|
| Q1 | **Backend language.** Earlier you described a Java framework; the v2 plan moved to one Python (FastAPI) backend because LangGraph is Python. Your new brief uses Java-style layer names (controllers, services, repositories, DTOs). Which is it? | **Python 3.12 + FastAPI**, with the layers named exactly as you listed. If you choose Java (Spring or your own framework), Layers 1 to 3 are Java and Layer 4's LangGraph part becomes a small Python service. I would then rewrite `backend.md` and the paths in `CLAUDE.md` before coding |
| Q2 | **Paytm credentials.** Do you have Paytm staging merchant ID and key? Do you know whether EMI plans are configured on that merchant? | **No keys assumed.** Layer 1 builds the real Paytm adapter against recorded and documented request shapes, but the Mock adapter is the active default. We flip to real when keys exist |
| Q3 | **Who writes the code?** You asked for a plan Claude Code can execute. After approval, do you want me to (a) give you the Layer 1 kickoff prompt to paste into Claude Code, or (b) write the Layer 1 code here in this chat as a diff? | **(a)** Claude Code executes; I stay your planner and reviewer. Section 7 has the prompt |
| Q4 | **Timeline intent.** Is this plan for tomorrow's hackathon build window, or for the codebase you will submit and continue after the event? (See Section 4: the full plan cannot fit in one day.) | **Both:** tonight Layer 1, then a compressed version of Layers 2 and 3 on Sunday, Layer 4 as far as time allows |
| Q5 | **Layer 1 scope.** "Payment API connection" alone cannot run without a project skeleton, a database and the EMI engine used to cross-check Paytm's numbers. May Layer 1 include: repo bootstrap, Money and EMI engine, persistence for payment attempts and audit events, then the gateway layer? | **Yes.** Called "Foundation + Payment gateway integration" |
| Q6 | **LangGraph scope.** v2 sketched a graph for the whole customer session. For learning and review I propose a plain state machine in the deterministic core (Layers 2 and 3) and LangGraph **only for the AI flows in Layer 4** (explain, audit, fallback, teach-back, weekly message). OK? | **Yes**, so the core runs and is tested without LangGraph installed |

**Needed before Layer 2 or later**

| # | Question | Default |
|---|---|---|
| Q7 | M1 says the pairing PIN comes from an "owner app", which is not in the design. How are PINs created for the demo? | Seeded demo merchant and PIN through a one-off seed command; no owner app |
| Q8 | M5 has **Share with brand rep**. What should it do? | Generates a shareable text summary and copies it (no real sending) |
| Q9 | M5's weekly message has a "sent" state. Real WhatsApp/SMS or simulated? | Simulated (marked as sent in the database) |
| Q10 | Which model writes the explanation text in Layer 4? Do the Sarvam credits cover its text model? | Use Sarvam's text model if covered; otherwise one hosted LLM behind the same port |
| Q11 | Frontend as a pnpm monorepo with **two apps** (merchant-web, customer-web) plus shared `ui-kit`, `api-client`, `shared-i18n` packages | Yes |
| Q12 | Git host and review tool. You said "MR", which suggests GitLab. | GitLab-style MRs; commands in `git-workflow.md` work on any host |
| Q13 | Who reviews the Tamil strings before the demo? | A native speaker you nominate; strings stay marked as drafts until then |
| Q14 | Cooling-off period wording: placeholder until a lender confirms | Keep the placeholder |

---

## 3. Findings from reviewing the design

I read the canvas files and the earlier plan documents. Points a mentor would raise:

1. **Merchant privacy is stricter in the design than in the v2 plan.** v2's "live session" screen showed step-by-step customer progress. The design shows only **Choosing** and **Ready to pay**. I follow the design (it is the stricter rule) and have written it into `CLAUDE.md`.
2. **The design implies an "owner app"** (M1) that does not exist (Q7).
3. **The mockup files are Design Component pages, not React.** They are a reference for layout, states and the Tamil and English string tables, not code to port. `frontend.md` tells the frontend agent to build real components from them.
4. **The mockups use sample data throughout** (shop, products, funnel counts, settlement batches). `DESIGN_SPEC.md` lists it so the seed data matches the screens exactly.
5. **Settlement data is not available on Paytm staging** (at least one settlement detail endpoint is documented as production-only, from the v2 research **[Verify]**). It is behind its own `SettlementPort` with a Mock, and labelled.
6. **Layer order and dependencies.** The merchant UI needs sales, QR tokens and reports; the customer UI needs budgets, comfort, consent. I therefore give **each UI layer its own backend slice** (a vertical slice) rather than building all backend first. This keeps each MR demonstrable.
7. **Honest limits stay visible:** lender decisions, account data and settlement data are mocked or synthetic.

---

## 4. Timeline reality check **[Inferred]**

Estimates for working with Claude Code, including review pauses. They are my estimates, not measurements.

| Layer | Build | Review and fixes | Total |
|---|---|---|---|
| 1. Foundation + gateway | 3 to 4 h | 1 h | about 4 to 5 h |
| 2. Merchant UI + slice | 4 to 5 h | 1 h | about 5 to 6 h |
| 3. Customer UI + slice | 5 to 6 h | 1 h | about 6 to 7 h |
| 4. Sarvam AI | 3 to 4 h | 1 h | about 4 to 5 h |
| **All four** | | | **about 19 to 23 h** |

Tomorrow's build window is roughly 09:30 to 12:00, then mentor rounds and hacking until 16:00. **The full plan will not fit between now and the demo** if every layer pauses for a full MR review.

**Recommended compression for the event** (your decision, Q4):
- **Tonight:** Layer 1 complete with Mock adapter default; start Layer 2 backend slice.
- **Sunday:** run Layers 2 and 3 with lighter reviews (reviewer agent plus a skim), prioritise the happy path C1, C2, C4, C7, C9, C10 and M1 to M5. Layer 4 starts with the template explanation and Sarvam text-to-speech only; speech-to-text and teach-back are stretch.
- **After the event:** finish each layer to the full standard, with proper MRs.

Whatever you choose, the rules, tests and the number audit are **never** skipped.

---

## 5. Proposed folder structure

```
emi-copilot/
├── CLAUDE.md
├── IMPLEMENTATION_PLAN.md
├── Makefile  docker-compose.yml  .env.example  .gitignore  .pre-commit-config.yaml
├── .claude/agents/
│   ├── architect.md  backend-engineer.md  frontend-engineer.md  reviewer.md
├── docs/
│   ├── rules/   backend.md  frontend.md  api-conventions.md  testing.md
│   │            git-workflow.md  design-patterns.md  security-and-compliance.md
│   ├── design/  DESIGN_SPEC.md  mockups-source/
│   ├── handoff/ LAYER-1-HANDOFF.md ... (written at each gate)
│   └── adr/     0001-... (one file per decision)
├── backend/
│   ├── pyproject.toml  alembic.ini  alembic/versions/
│   ├── src/emi_copilot/
│   │   ├── main.py
│   │   ├── config/settings.py
│   │   ├── api/controllers/        gateway_controller.py, merchant_controller.py, ...
│   │   ├── api/dependencies.py  api/error_handlers.py
│   │   ├── services/               offer_discovery_service.py, payment_handoff_service.py, ...
│   │   ├── repositories/           payment_attempt_repository.py, audit_event_repository.py, ...
│   │   ├── models/                 payment_attempt.py, audit_event.py, ...
│   │   ├── dtos/                   offer_dtos.py, payment_link_dtos.py, ...
│   │   ├── domain/
│   │   │   ├── money.py  errors.py  events.py
│   │   │   ├── emi/                emi_calculation_strategy.py, reducing_balance_strategy.py, no_cost_strategy.py
│   │   │   ├── comfort/  ranking/  (Layer 3)
│   │   ├── adapters/
│   │   │   ├── payment_gateway/    port.py, paytm_adapter.py, mock_adapter.py, factory.py,
│   │   │   │                       checksum_signer.py, paytm_error_translator.py
│   │   │   ├── settlement/         port.py, mock_adapter.py
│   │   │   └── ai/                 (Layer 4)
│   │   ├── events/                 event_bus.py, audit_subscriber.py, ...
│   │   └── core/                   resilient_http_client.py, logging.py, clock.py, id_generator.py
│   └── tests/ unit/ integration/ contract/
└── frontend/
    ├── package.json  pnpm-workspace.yaml  tsconfig.base.json
    ├── apps/merchant-web/src/{app,features,pages,i18n}
    ├── apps/customer-web/src/{app,features,pages,i18n}
    └── packages/{ui-kit,api-client,shared-i18n}
```

Rule documents (all delivered with this plan): `CLAUDE.md`, `backend.md`, `frontend.md`, `api-conventions.md`, `testing.md`, `git-workflow.md`, `design-patterns.md`, `security-and-compliance.md`, plus `DESIGN_SPEC.md`.

---

## 6. Execution model: agents, sessions and hand-off

### 6.1 How the agents divide the work

**[Fact, from Claude Code docs and guides]** The main Claude Code session coordinates; custom subagents live in `.claude/agents/`, run in their own context with restricted tools, **cannot spawn other subagents**, do not see the main conversation, and return only a final message. Project `CLAUDE.md` is loaded into subagents. **[Verify]** version-specific details against the current Claude Code documentation.

| Agent | Responsibility | Used in |
|---|---|---|
| **Orchestrator** (main session) | Reads the handoff, runs plan mode, delegates, integrates, runs gates, writes summaries | All layers |
| **architect** (read-only) | Layer plan, pattern choice, open questions | Start of every layer |
| **backend-engineer** | Domain, persistence, adapters, services, controllers, tests | Layers 1 to 4 |
| **frontend-engineer** | ui-kit, screens, hooks, i18n, UI tests | Layers 2, 3, and part of 4 |
| **reviewer** (read-only plus checks) | Diff review against the rules | End of every layer |

Because subagents see nothing but their brief, **every delegation names the goal, the files to read, and the acceptance criteria.**

### 6.2 Sessions (four, one per layer)

| Session | Layer | Starts from | Ends with |
|---|---|---|---|
| **S1** | Foundation + Layer 1 (gateway) | Empty repo plus this docs pack | MR for `layer/1-payment-gateway`, `LAYER-1-HANDOFF.md` |
| **S2** | Layer 2 (merchant) | `main` after the Layer 1 MR is merged | MR for `layer/2-merchant-ui`, `LAYER-2-HANDOFF.md` |
| **S3** | Layer 3 (customer) | `main` after Layer 2 | MR for `layer/3-customer-ui`, `LAYER-3-HANDOFF.md` |
| **S4** | Layer 4 (Sarvam AI) | `main` after Layer 3 | MR for `layer/4-sarvam-ai`, `LAYER-4-HANDOFF.md` |

A layer may need more than one sitting if a context window fills up. In that case ask Claude Code to write a checkpoint into the handoff file and start a fresh session with the same opening prompt.

### 6.3 Hand-off protocol

A new session knows nothing. Continuity lives in files:

1. **`CLAUDE.md` status table** shows which layer is done.
2. **`docs/handoff/LAYER-N-HANDOFF.md`** (template below) holds what was built, decisions, commands, and open items.
3. **`docs/adr/`** holds one short file per decision made during the layer.
4. **Opening prompt for every session:** "Read CLAUDE.md, the latest file in docs/handoff/, and docs/rules/. Then run the architect agent for Layer N and show me the plan. Do not write code until I approve."

**Handoff file template**

```
# LAYER-N-HANDOFF
## Built (files and endpoints or screens)
## Why (decisions, with ADR links)
## Patterns used (pattern, file, problem solved)
## How to run and verify (exact commands)
## Test and coverage results
## Known limitations and mocks
## Open questions for the next layer
## Next layer prerequisites
```

---

## 7. How to start (one-time setup for you)

1. Create the repository `emi-copilot` and copy this folder's contents into its root (`CLAUDE.md`, `IMPLEMENTATION_PLAN.md`, `docs/`, `.claude/`).
2. Commit them on `main` as `docs(rules): add project rules, design spec and agent definitions`.
3. Open Claude Code at the repository root. Confirm the four agents appear and that `CLAUDE.md` loads. **[Verify]** the commands for listing agents and memory in your Claude Code version.
4. Paste the **Layer 1 kickoff prompt** (Section 8.1) once you have answered Section 2 and I have updated the defaults.

---

## 8. The layers

Each layer follows the same shape: objective, what you will learn, steps (each with What, Why and Review), patterns, tests, acceptance criteria, gate.

### 8.1 Layer 1: Foundation + Payment gateway integration (Session S1)

**Objective.** A runnable backend that can discover EMI offers and create and track a Paytm payment handoff, behind a port so a Mock and the real Paytm adapter are interchangeable. Money maths is correct to the paise.

**You will learn:** hexagonal architecture (ports and adapters), value objects for money, strategy-based EMI maths, resilient external calls, idempotency, event-driven audit.

**Agents:** architect (plan), backend-engineer (steps 1.0 to 1.9), reviewer (gate).

| Step | What | Why | Review focus |
|---|---|---|---|
| **1.0 Bootstrap** | Repo layout, `pyproject.toml`, Makefile, Docker Compose with PostgreSQL, settings class, `.env.example`, pre-commit, logging with correlation IDs, `/health` | A consistent base so every later step is checked automatically | `make check` runs green; no secrets committed |
| **1.1 Money value object** | `Money` (Decimal, paise, half-up rounding, no float) with tests | Rounding mistakes in money are the costliest bug class; one place owns them | Property tests; no float anywhere |
| **1.2 EMI calculation** | `EmiCalculationStrategy` with `ReducingBalanceStrategy` and `NoCostStrategy`; last installment absorbs remainder | Strategy lets rules vary without touching callers | Hand-checked table incl. the three design plans; hypothesis properties from `testing.md` |
| **1.3 Persistence** | Models and migration for `payment_attempt` and `audit_event`; repositories; unit of work | Idempotent payments and an audit trail need storage | Append-only `audit_event`; indexes; reversible migration |
| **1.4 Gateway port** | `PaymentGatewayPort` in domain terms (`discover_offers`, `create_payment_link`, `get_payment_status`, `verify_webhook`) and domain types | Services depend on an interface, never on Paytm field names | No vendor terms leak into the port |
| **1.5 Mock adapter** | `MockPaymentGatewayAdapter` returning the design's sample plans and deterministic statuses (`SettlementPort` moved to Layer 2, ADR 0006) | Develop and test with no network or keys | Mock announced in startup log |
| **1.6 Resilient HTTP client** | Timeouts, retry with jitter for idempotent calls only, circuit breaker | One slow dependency must not take the system down | Initiate calls are never retried |
| **1.7 Paytm adapter** | `PaytmPaymentGatewayAdapter`: checksum signing, offer discovery, payment link creation with the chosen offer, status check, webhook verification, `PaytmErrorTranslator`; contract tests against recorded fixtures | The real integration, isolated behind the port | Endpoint shapes marked **[Verify]** against current Paytm docs; no real IDs in fixtures |
| **1.8 Factory, events, services** | `PaymentGatewayFactory`; `DomainEventBus` (Observer) with audit subscriber; `OfferDiscoveryService`, `PaymentHandoffService`, `PaymentStatusService` | Config chooses Mock or real; audit stays decoupled | Services import ports only |
| **1.9 Controllers and docs** | `GET /offers`, `POST /payment-links` (needs `Idempotency-Key`), `GET /payments/{orderId}/status`, `POST /webhooks/paytm`; problem+json errors; OpenAPI export | The public contract the UIs will use | Matches `api-conventions.md`; webhook rejects bad signatures |

**Patterns:** Port and Adapter, Factory, Strategy, Repository, Value Object, DTO, Observer, Unit of Work, Circuit Breaker and Retry.

**Acceptance criteria**
- [ ] `make check` passes; domain and audit-related code at 100% coverage, overall at least 85%.
- [ ] The three sample plans on ₹22,000 compute to: no-cost 5 x ₹3,666.67 + ₹3,666.65 (displays ₹3,667 x 6, sums to exactly ₹22,000.00), ₹3,850.00 x 6 and ₹2,050.00 x 12, with extras ₹0, ₹1,100 and ₹2,600 (ADR 0001).
- [ ] Swapping Mock and Paytm adapters is a configuration change only; contract tests pass for both.
- [ ] A timed-out create-link call surfaces a typed error and is **not** retried; the same `Idempotency-Key` returns the original result.
- [ ] A webhook with a bad signature is rejected and audited; a repeated valid webhook has no extra effect.
- [ ] No card fields exist anywhere; no secrets in the repo.
- [ ] OpenAPI is exported and valid.

**Gate output (I produce this):** layer summary (what, why, patterns, what to review), `LAYER-1-HANDOFF.md`, the MR description, and the diff commands from `git-workflow.md`. **Then I stop and ask for your go-ahead for Layer 2.**

**Layer 1 kickoff prompt (paste into Claude Code in S1; finalised after Section 2)**

```
Read CLAUDE.md, docs/rules/*, docs/design/DESIGN_SPEC.md and IMPLEMENTATION_PLAN.md section 8.1.
We are building Layer 1: Foundation + Payment gateway integration, on branch layer/1-payment-gateway.
Start in plan mode. Run the architect agent and show me the plan, patterns and any open questions.
Do not write code until I approve. After approval, delegate to backend-engineer one step at a time
(1.0 to 1.9), one commit per step in the format from git-workflow.md, and run make check before each commit.
Ask me if anything is ambiguous. At the end run the reviewer agent, write docs/handoff/LAYER-1-HANDOFF.md,
update the status table in CLAUDE.md, show the layer summary, and stop for my confirmation.
```

### 8.2 Layer 2: Merchant UI + merchant backend slice (Session S2)

**Objective.** A tablet-first merchant app: pair the device, pick a product, show a QR, see who is choosing or ready to pay, hand off to Paytm, and read the sales report. The backend slice supports exactly these screens.

**You will learn:** vertical slicing, a state machine for sales, Server-Sent Events, OpenAPI-generated clients, design tokens and a shared UI kit, accessible components.

**Agents:** architect, backend-engineer (slice), frontend-engineer (UI), reviewer.

**Prerequisites:** Layer 1 merged; Q7, Q8, Q9, Q11 answered; mockup sources present in `docs/design/mockups-source/`.

| Step | What | Why | Review focus |
|---|---|---|---|
| **2.1 Backend: merchants and catalogue** | Models, migrations, repositories for `merchant`, `device_pairing`, `product`; seed command matching `DESIGN_SPEC` sample data; pairing PIN to bearer token; rate limiting | Real auth boundaries from day one | Merchant can read only own data; PIN throttling |
| **2.2 Backend: sales and QR** | `Sale` with `SaleStateMachine` (`CHOOSING`, `READY_TO_PAY`, `PAID`, `FAILED`, `EXPIRED`); signed expiring QR token; `POST /sales`, `GET /sales`; funnel events recorded through the event bus | Legal transitions explicit and tested | Illegal transitions rejected; token expiry |
| **2.3 Backend: live status and handoff** | SSE feed of sale status (merchant sees only Choosing or Ready to pay); handoff endpoint reusing Layer 1 service (payment link or EDC instructions); status polling fallback | Real-time feel without exposing customer detail | Response schemas contain no income, EMI, ratio or step history (tested) |
| **2.4 Backend: reports** | Funnel, missed-sales and budget buckets, money-due via `SettlementPort` mock, suggested actions (deterministic rules), weekly message as a template (AI comes in Layer 4) | The merchant value of the product | Dashboard counts reconcile with the database (test) |
| **2.5 Frontend workspace** | pnpm workspace, `ui-kit` with tokens and base components (Button, Chip, Card, Tabs, ExpandableCard, LanguageToggle, StatusChip, FunnelBar, QrPanel), `api-client` generated from OpenAPI, i18n setup | One source of design truth; no hand-written API types | Tokens only, no hard-coded colours; axe passes |
| **2.6 merchant-web screens** | M1 pairing, M2 new EMI sale and counter list, M3 show QR (tablet and phone), M4 handoff and status, M5 sales report with expandable cards and EN / தமிழ் toggle, M8 weekly message | The merchant journey from the design | Every state in `DESIGN_SPEC` section 6 handled |
| **2.7 Tests and docs** | Component tests with axe, hook tests, Playwright merchant path against the Mock gateway | Proof it works end to end | No live network |

**Patterns:** State, Observer (SSE broadcaster), Repository, Strategy (suggested actions), Container and Presentational components, Adapter (API client).

**Acceptance criteria**
- [ ] M1 to M5 and M8 match the mockups in layout, copy and states, in English and Tamil.
- [ ] Merchant APIs never return customer income, EMIs, ratios or step history (schema test).
- [ ] Sale transitions follow the state machine; expired QR tokens are rejected.
- [ ] Report numbers equal the design's sample data when seeded.
- [ ] `make check`, axe and the Playwright merchant path pass.

**Gate:** summary, `LAYER-2-HANDOFF.md`, MR description, then **stop and ask before Layer 3**.

### 8.3 Layer 3: Customer UI + customer backend slice (Session S3)

**Objective.** The phone flow from QR scan to receipt, including the consented comfort check, ranking, smarter alternatives, OTP consent with evidence, and handoff status.

**You will learn:** a flow state machine on the client, deterministic comfort and ranking engines, append-only consent evidence, privacy by design, accessibility in two languages.

**Agents:** architect, backend-engineer, frontend-engineer, reviewer.

**Prerequisites:** Layer 2 merged; Q13, Q14 answered.

| Step | What | Why | Review focus |
|---|---|---|---|
| **3.1 Backend: customer sessions** | QR token exchange for a session token bound to one sale; language preference; budget endpoint with confirmation | Customers need no account but must stay isolated | Single-sale binding; token never logged |
| **3.2 Backend: comfort engine** | `ComfortRatio`, `ComfortBandClassificationStrategy` (35% and 50% heuristics from one config class), synthetic profile provider behind a port | Advice without a credit decision | Boundary tests at exactly 35% and 50%; wording rules |
| **3.3 Backend: ranking and alternatives** | `PlanRankingStrategy` with reason codes; "no plan fits" keeps all plans; down payment, tenure and cheaper-model alternatives recomputed by the engine | All logic server-side; UI only displays | Never hides a plan; sort stability |
| **3.4 Backend: consent and receipt** | OTP via a mock OTP port, `ConsentRecord` append-only and hash-chained with the frozen plan snapshot, receipt, handoff trigger, `TemplateExplanationService` | Consent is evidence | No update or delete path; chain verification test |
| **3.5 customer-web foundation** | App shell, flow reducer with typed steps, language persistence, money formatting util | The customer cannot reach consent without confirmed budget and selected plan | Reducer coverage 100% |
| **3.6 customer-web screens** | C1 to C10 with all states from `DESIGN_SPEC` section 5 | The customer journey from the design | Plan cards show monthly and extra at the same size |
| **3.7 Tests and docs** | Component and axe tests; Playwright full happy path (merchant and customer) in English and Tamil; privacy tests | End-to-end confidence | OTP wrong and expired states calm and correct |

**Patterns:** Strategy (comfort, ranking), State (flow reducer), Repository, Value Object, Template fallback, Unit of Work, Observer (funnel events).

**Acceptance criteria**
- [ ] Happy path C1, C2, C3, C4, C6, C7, C9, C10 completes in English and Tamil with sample data matching the design.
- [ ] Skipping the comfort check is allowed and plans show without bands.
- [ ] No plan is ever hidden; "no plan fits" labels plans "above your budget".
- [ ] Consent rows are append-only with a verifiable hash chain and store the exact plan shown.
- [ ] Merchant never sees customer financial data (cross-layer test).
- [ ] `make check`, axe and Playwright pass.

**Gate:** summary, `LAYER-3-HANDOFF.md`, MR, then **stop and ask before Layer 4**.

### 8.4 Layer 4: Sarvam AI integration (Session S4)

**Objective.** Add voice and AI-written explanations safely: Sarvam speech-to-text and text-to-speech, an explanation flow with a mandatory number audit and template fallback, advisory teach-back, and an AI-written weekly message.

**You will learn:** wrapping external AI behind ports, decorators for guardrails, LangGraph for small deterministic flows with fallbacks, tracing and cost tracking, testing AI without calling AI.

**Agents:** architect, backend-engineer, frontend-engineer (audio and mic UI), reviewer.

**Prerequisites:** Layer 3 merged; Q6 and Q10 answered; Sarvam API key available; Sarvam model names confirmed **[Verify]** against current docs.

| Step | What | Why | Review focus |
|---|---|---|---|
| **4.1 Ports and mocks** | `SpeechPort`, `ExplanationTextPort`, Mock implementations returning fixed text and audio | Everything testable with no network | AI has no tools and no database access |
| **4.2 Number audit** | `NumberAuditService`: extract every number from AI text, normalise (Tamil numerals, grouping), compare with engine output | The core safety control | 100% coverage; one wrong digit forces fallback |
| **4.3 Sarvam speech adapter** | `SarvamSpeechAdapter` for speech-to-text and text-to-speech with resilient client, timeouts, audio never stored | Voice for low-literacy users | Audio streamed and discarded; **[Verify]** current API shape |
| **4.4 Explanation text adapter** | Provider chosen in Q10 behind `ExplanationTextPort`; structured input only (plans and reason codes, no personal data) | Swappable provider | No personal data in prompts |
| **4.5 LangGraph flows** | Explain, then audit, then fallback to template; teach-back scoring (advisory); weekly merchant message, then audit. No cycles, no tool-calling nodes, recursion limit set | Small, inspectable graphs where branching helps | Core still runs without LangGraph installed |
| **4.6 Decorator and tracing** | `AuditedExplanationService` wraps the AI service; OpenTelemetry and Langfuse tracing with redaction; cost and latency logged per session | Guardrails without touching adapters | Traces contain no personal data |
| **4.7 API and frontend** | `POST .../explanation`, `.../speech/transcriptions`, `.../speech/synthesis`, `.../teach-back`, `GET /reports/weekly-message`; audio playback on C7, mic on C2 and C8 with on-screen confirmation, AI-written weekly message on M5 and M8 | Brings the AI into the screens | "AI unavailable" shows the standard text with no banner |
| **4.8 Tests and docs** | Golden tests with fixed AI outputs including a wrong-number case; chaos test (AI down); Tamil copy review checklist; README honest-limits section | Prove safety and resilience | No live calls in CI |

**Patterns:** Port and Adapter, Decorator, Factory, Strategy (provider), Template fallback, Circuit Breaker, Observer (tracing events).

**Acceptance criteria**
- [ ] No AI-written number reaches a user unless it passed the audit; a deliberate wrong number triggers the template fallback (tested and shown).
- [ ] With the AI provider disabled, every screen still works with standard text and no error banner.
- [ ] Voice is optional; every spoken number is also on screen.
- [ ] No personal data in prompts or traces; audio is never stored.
- [ ] Cost per session and latency are logged.
- [ ] `make check` and Playwright (including the AI-down path) pass.

**Gate:** summary, `LAYER-4-HANDOFF.md`, MR, final reviewer pass, README with architecture diagram and honest limits.

---

## 9. Layer gate protocol (applies to every layer)

1. Orchestrator runs the **reviewer** agent and fixes blocking issues.
2. Orchestrator produces the **layer summary** (template below), the MR description, and the diff commands output.
3. Orchestrator writes the handoff file and updates the `CLAUDE.md` status table.
4. Orchestrator **stops** and asks: "Layer N is ready for your review. Shall I continue to Layer N+1?" It does not proceed on silence.

**Layer summary template**

```
## Layer N summary
Built: ...
Why: ...
Patterns used: pattern, file, problem solved
Review first: up to 5 files and what to look for
Tests: counts and coverage
Limitations and mocks: ...
Questions for you: ...
```

---

## 10. Defaults I chose (tell me to change any)

Python 3.12 with FastAPI; synchronous SQLAlchemy 2.0 for readability; PostgreSQL via Docker Compose; camelCase JSON on the wire with money in integer paise; RFC 7807 errors; pnpm monorepo with two Vite apps; Tailwind driven by the design tokens; TanStack Query; react-i18next; Playwright for happy paths only; Conventional Commits; one branch and one MR per layer; coverage targets in `testing.md` (my proposals, not facts).

## 11. Risks to this plan

| Risk | Mitigation |
|---|---|
| Not enough time before Sunday | Compression plan in Section 4; rules and number audit never skipped |
| Subagents lose context | Every delegation includes goal, files and acceptance criteria; handoff files carry state |
| Design and spec drift | Spec is distilled from the mockups; disagreements stop the work and become questions |
| Paytm endpoints differ from my recollection | Real adapter built against docs and fixtures, marked **[Verify]**, Mock is the default until keys exist |
| Tamil text errors | Strings marked as drafts; native review before the demo |
| Over-engineering for a hackathon | Patterns catalogue lists the problem each solves; reviewer flags patterns that do not earn their place |
