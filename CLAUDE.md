# CLAUDE.md: EMI-at-Counter Copilot

Project-wide rules for Claude Code. Read this first in every session. Keep it short; detail lives in the imported rule files.

> **Decision status:** items marked `[DEFAULT]` were chosen by the planner and may be changed by the owner. Items marked *Decided* were confirmed by the owner. If a decision changes, update this file and every rule file that mentions it before writing code.

## 1. What we are building

**Positioning:** Paytm makes EMI available. We make it affordable and understood, and show merchants why they lose sales.

A customer buys an electronics item at a shop. The **merchant** starts a sale on a tablet. The **customer** scans a QR on their own phone, states a comfortable monthly amount, sees EMI plans compared honestly (monthly amount **and** extra cost in total), optionally runs a consented **comfort check**, hears or reads a plain Tamil/English explanation, consents with an OTP, and is **handed off to Paytm** for payment. The merchant gets a sales report: where customers drop off, missed sales, and money due from brands.

This is a hackathon product built to production-quality standards so a mentor can review it. Event: Paytm Build for India AI Hackathon, Chennai, Track 2.

## 2. Non-negotiable rules (never break, never "just for the demo")

1. **AI sits beside the money path, never in it.** AI explains, transcribes and summarises. Deterministic code calculates, ranks and validates. AI components have **no tools** and cannot call payment, consent or database-write functions.
2. **Every number in AI text must be verified** by the number-audit component against engine output. Mismatch means fall back to the template text. No exceptions.
3. **No card data.** Never receive, log, store or accept card number, expiry or CVV anywhere. Payment happens on Paytm after handoff.
4. **Money is never a float.** Use `Decimal` in domain code and **integer paise** in the database and on the wire.
5. **Comfort bands are exactly three:** Comfortable, Stretching, Risky. Never "approved", "declined", "eligible for credit" or "rejected". The comfort check is advice, not a credit decision.
6. **Merchant privacy:** the merchant never sees a customer's income, existing EMIs, comfort ratio or step-by-step progress. Merchant APIs expose only: sale status `CHOOSING` or `READY_TO_PAY`, the chosen plan, totals, and aggregates.
7. **Plain wording on customer screens.** Say "extra you pay", not "interest rate". Show "Each month ₹X for N months" beside "Extra in total ₹Y on top of the price" at the same size. No "best for you", no urgency language.
8. **Consent is evidence.** Consent records are append-only, hash-chained and store the exact plan snapshot shown.
9. **Human gates stay human:** customer confirms the budget, consents to the comfort check, selects the plan and gives OTP consent; the merchant performs the payment step on Paytm.
10. **Mocks are labelled.** Anything not real (lender decision, settlement data, account-aggregator data) goes through a mock adapter whose name contains `Mock` and is announced in startup logs.

## 3. Architecture overview

```
React PWAs (merchant-web, customer-web)
        | REST /api/v1 (camelCase JSON, money in paise)
FastAPI backend  [Decided: Python 3.12]
  api/controllers  ->  services  ->  repositories  ->  PostgreSQL
                          |
                          +-> domain (pure: Money, EMI engine, comfort engine, ranking)
                          +-> adapters (ports + implementations)
                                - payment_gateway: Paytm adapter | Mock adapter
                                - ai (Layer 4): Sarvam speech, LLM text, number audit
                          +-> events (observer: audit, metrics, notifications)
```

Dependency direction: `controllers -> services -> (repositories, adapters, domain)`. `domain` imports nothing from the rest of the app. Controllers never touch repositories or adapters directly.

## 4. Stack

| Area | Choice | Status |
|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync), Alembic, httpx | Decided: Python. Library choices DEFAULT |
| Database | PostgreSQL 16 via Docker Compose | DEFAULT |
| AI orchestration | LangGraph for AI nodes only (Layer 4); no LangChain | Decided: LangGraph approved |
| Speech | Sarvam AI (speech-to-text, text-to-speech), credits provided | Decided |
| Frontend | React 18, TypeScript (strict), Vite, Tailwind with design tokens, TanStack Query, react-i18next, pnpm workspaces | DEFAULT |
| Tests | pytest, hypothesis, Vitest, Testing Library, Playwright (happy path only) | DEFAULT |
| Tooling | uv, ruff, mypy (strict), ESLint, Prettier, pre-commit | DEFAULT |

## 4a. Decisions already made (do not re-ask)

| # | Decision | Detail |
|---|---|---|
| D1 | Backend language | **Python 3.12 with FastAPI.** Layers are named controllers, services, repositories, models, DTOs, adapters |
| D2 | Paytm credentials | **None available.** The Mock payment gateway adapter is the default. The real Paytm adapter is built and tested against recorded fixtures and documented request shapes, and enabled only when staging keys exist (`PAYMENT_GATEWAY_MODE=paytm`) |
| D3 | Who executes | **Claude Code** executes each layer from the prompts in `PROMPTS.md` |
| D4 | Layer 1 scope | Foundation (repo, database, Money, EMI engine) plus the payment gateway layer |
| D5 | LangGraph | Used **only for the AI flows in Layer 4**; the core runs and is tested without it |
| D6 | Timeline | Event is Sunday 15 Nov 2026. If time is short the owner will say "event mode": lighter reviews, happy path first. Rules, tests for money maths and the number audit are never skipped |
| D7 | Claude artifact link | **Claude Code cannot open the design link.** Use `docs/design/DESIGN_SPEC.md` and `docs/design/mockups-source/` only |

## 5. Repository layout

```
emi-copilot/
  CLAUDE.md                  this file
  docs/
    rules/                   backend.md, frontend.md, api-conventions.md, testing.md,
                             git-workflow.md, design-patterns.md, security-and-compliance.md
    design/                  DESIGN_SPEC.md, mockups-source/ (reference .dc.html files)
    handoff/                 LAYER-N-HANDOFF.md written at the end of each layer
    adr/                     architecture decision records (one file per decision)
  .claude/agents/            architect, backend-engineer, frontend-engineer, reviewer
  backend/                   see docs/rules/backend.md
  frontend/                  see docs/rules/frontend.md
  docker-compose.yml  Makefile  .env.example
```

## 6. Imported rule files

@docs/rules/backend.md
@docs/rules/frontend.md
@docs/rules/api-conventions.md
@docs/rules/testing.md
@docs/rules/git-workflow.md
@docs/rules/design-patterns.md
@docs/rules/security-and-compliance.md
@docs/design/DESIGN_SPEC.md

## 7. Coding standards (apply to all code)

- **Readable names.** Fully spelled, self-explanatory: `calculateMerchantSettlementAmount`, not `calcAmt`. Python uses `snake_case` (`calculate_merchant_settlement_amount`); TypeScript uses `camelCase`. No abbreviations except universally known ones (`id`, `url`, `otp`, `emi`).
- **One comment per method or function:** one or two lines saying its purpose, e.g. `# Connects to the Sarvam AI API and handles request retry logic.` (Python docstring first line, or `//` above a TypeScript function).
- **Name the pattern in the code.** Where a design pattern is used, say so once on the class: `# Pattern: Adapter. Wraps the Paytm HTTP API behind PaymentGatewayPort.` See `design-patterns.md`.
- **Small units.** One responsibility per class, function and file. Soft limits: function 30 lines, class 200 lines, file 300 lines, React component 150 lines. Exceeding a limit needs a one-line justification in the PR.
- **No dead code, no commented-out code, no TODO without a linked issue.**
- **Comments explain why, not what.** Names explain what.
- **Errors are explicit.** Typed domain errors; no bare `except`; no swallowed exceptions.

## 8. How to work (every layer)

1. **Plan first.** Start in plan mode. Read `docs/handoff/` (latest file) and the relevant rule files. Produce a short plan; wait for approval.
2. **Small commits** following `git-workflow.md`, on the layer branch.
3. **Test as you go.** Write the test with or before the code. Run `make check` before every commit.
4. **Explain as you build.** After each step, add a short "What / Why / Review" note in the commit body.
5. **Ambiguity rule.** If a design decision is missing or two documents disagree, **stop and ask**. Do not guess. Record the answer in `docs/adr/`.
6. **Layer gate.** At the end of a layer: run the reviewer agent, produce the layer summary, write `docs/handoff/LAYER-N-HANDOFF.md`, update the status table below, then **stop and ask for confirmation** before starting the next layer.

## 9. Agents (orchestrator model)

The **main Claude Code session is the orchestrator**. Subagents cannot spawn other subagents and do not see the main conversation, so every delegation must include the goal, the files to read, and the acceptance criteria.

| Agent | File | Role | Tools |
|---|---|---|---|
| architect | `.claude/agents/architect.md` | Layer plan, boundaries, ADRs; read-only | Read, Grep, Glob |
| backend-engineer | `.claude/agents/backend-engineer.md` | Backend code and tests | Read, Edit, Write, Bash, Grep, Glob |
| frontend-engineer | `.claude/agents/frontend-engineer.md` | UI code and tests | Read, Edit, Write, Bash, Grep, Glob |
| reviewer | `.claude/agents/reviewer.md` | Reads the diff against the rules; read-only plus running checks | Read, Grep, Glob, Bash |

## 10. Layer status (orchestrator updates this table at every gate)

| Layer | Scope | Branch | Status |
|---|---|---|---|
| 1 | Foundation + Payment gateway integration | `layer/1-payment-gateway` | Done; MR ready for owner review (see `docs/handoff/LAYER-1-HANDOFF.md`) |
| 2 | Merchant UI + merchant backend slice | `layer/2-merchant-ui` | Not started |
| 3 | Customer UI + customer backend slice | `layer/3-customer-ui` | Not started |
| 4 | Sarvam AI integration | `layer/4-sarvam-ai` | Not started |

## 11. Commands (created in Layer 1)

`make setup`, `make dev`, `make check` (lint + types + tests), `make test`, `make migrate`, `make openapi` (exports the OpenAPI schema used by the frontend client).

## 12. Out of scope

Real lending decisions, real account-aggregator integration, payment form or card entry, storing voice audio, an admin console, and any use of Paytm logos or copied Paytm assets.
