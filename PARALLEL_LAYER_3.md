# PARALLEL_LAYER_3.md: Running Layer 3 while Layer 2 is still in progress

**Situation:** Layer 1 is merged. Layer 2 is in progress at step 2.4. Time is short, so Layer 3 starts in a second Claude Code session before Layer 2 is merged.

**Verdict:** Yes, **partly**. Some Layer 3 work does not depend on Layer 2 at all. Some depends only on one Layer 2 step. Some must wait for the Layer 2 merge. Running everything in parallel from today would cause rework. The split below avoids that.

> This changes the rule "each layer branches from the latest main after the previous layer merges". Record it as **ADR 0012** (`docs/adr/0012-parallel-layer-3.md`, text in section 7). Numbers 0002 to 0011 are already used.

---

## 1. What can run in parallel

| Layer 3 piece | Depends on | Can start | Why |
|---|---|---|---|
| **3.2 Comfort engine** (`ComfortRatio`, band strategy, synthetic profile port) | Layer 1 only (`Money`) | **Now** | Pure domain code, no database, no web layer |
| **3.3 Ranking and alternatives** (ranking strategy, reason codes, down payment, tenure and cheaper-model recompute) | Layer 1 only (EMI engine) | **Now** | Pure domain code |
| **3.0 API contract** (customer DTOs and OpenAPI) | Layer 1 conventions | **Now** | Only Pydantic DTO files; no database |
| **3.5 / 3.6 Customer UI** (flow reducer, C1 to C10) | Layer 2 **step 2.5** (workspace, `ui-kit`, `api-client`, i18n setup) | **After 2.5 is committed** | The customer app reuses those packages |
| **3.1 Customer sessions** (QR token exchange) | Layer 2 sales, QR tokens, sale state machine | **After the Layer 2 merge** | Needs the `Sale` model and QR token code |
| **3.4 Consent and receipt, handoff trigger** | Layer 2 sales, migrations | **After the Layer 2 merge** | Needs `Sale` and shares the migration chain |
| **3.7 Integration tests, Playwright full path** | Everything | **After the Layer 2 merge** | Needs merchant and customer together |

Estimated saving: **about 1.5 to 2.5 hours** of the roughly 6 to 7 hours for Layer 3 **[Inferred, not measured]**. The cost is more of your attention, because you now review two streams.

---

## 2. Rules so the two sessions do not collide

1. **Two sessions, two folders.** Never run both in one working copy; each session switches branches and would overwrite the other's files. Use a git worktree:
   ```bash
   git worktree add ../emi-copilot-l3 -b layer/3-customer-ui main
   ```
   Open `../emi-copilot-l3` in a second VS Code window and start the second Claude Code session there.
2. **No database migrations in Layer 3 until Layer 2 is merged.** Two branches adding Alembic migrations create two heads. Pieces 3.0, 3.2, 3.3 and the UI need no migrations.
3. **File ownership.** Layer 3 only **adds new files**, plus one-line additions to shared index files such as `ui-kit/src/index.ts`. Layer 3 never edits Layer 2's merchant files.
   **Do not mount the Layer 3 routers in the app until Phase 3C.** In Phase 3A the stub routers exist as files but are not included in `api/dependencies.py` or the app factory, which Layer 2 is also changing. The contract's OpenAPI is exported by a small separate script that mounts only the customer router. The one-line mount happens in 3C after the second rebase, so any conflict there is small and happens once.
3a. **ADR numbering.** The Layer 2 session uses **0013 to 0019** (0012 is reserved for the parallel-work ADR). The Layer 3 session starts at **0020**.
3b. **Put the plan files in the Layer 3 branch first.** A worktree made from `main` does not contain `PARALLEL_LAYER_3.md` or ADR 0012. Add both as the **first commit on `layer/3-customer-ui`**, inside the new worktree, so the Layer 2 working tree is not disturbed:
   ```bash
   git worktree add ../emi-copilot-l3 -b layer/3-customer-ui main
   cp PARALLEL_LAYER_3.md ../emi-copilot-l3/
   cp docs/adr/0012-parallel-layer-3.md ../emi-copilot-l3/docs/adr/
   cd ../emi-copilot-l3
   git add PARALLEL_LAYER_3.md docs/adr/0012-parallel-layer-3.md
   git commit -m "docs(rules): add parallel Layer 3 plan and ADR 0012"
   ```
   (Run the `cp` lines from the folder where you saved the two files; they are not in the Layer 2 branch.)
4. **Only the Layer 2 session edits** `CLAUDE.md`'s status table and writes `LAYER-2-HANDOFF.md`. Layer 3 writes `docs/handoff/LAYER-3-WIP.md` instead and converts it at its own gate.
5. **Different ports.** Layer 2: backend 8000, merchant app 5173. Layer 3: backend 8001, customer app 5174.
6. **Layer 3 cannot be merged before Layer 2.** You may open the MR as a draft, but it merges only after Layer 2.
7. **Gates still apply.** Layer 2 still stops at its own gate. Layer 3 stops at its checkpoints; the final Layer 3 gate happens after integration.

---

## 3. Phased plan

| Phase | When | Session | Work |
|---|---|---|---|
| **3A** | Now, in parallel with Layer 2 | Layer 3 session, worktree | 3.0 contract, 3.2 comfort engine, 3.3 ranking and alternatives |
| **Sync point 1** | When Layer 2 commits step 2.5 | You | Rebase Layer 3 onto that commit (commands in section 5) |
| **3B** | After sync point 1, while Layer 2 finishes 2.6 and 2.7 | Layer 3 session | 3.5 flow reducer and 3.6 customer screens against a **fixture API** |
| **Sync point 2** | When Layer 2 is merged to `main` | You | Rebase Layer 3 onto `main` |
| **3C** | After sync point 2 | Layer 3 session | 3.1 customer sessions, 3.4 consent and receipt, swap fixture API for the real client, 3.7 tests, gate |

**Why the UI uses a fixture API first.** In `features/customer-flow/api/`, define one interface (for example `CustomerFlowApi`) with two implementations: `FixtureCustomerFlowApi` (returns the DESIGN_SPEC sample data) and `HttpCustomerFlowApi` (the generated client). A factory picks one by environment variable. This is the Adapter plus Factory pattern. Swapping to the real backend in 3C is then a one-line configuration change, and the UI tests stay valid. The contract from 3.0 is what keeps both implementations honest.

**Main risk:** the fixture API and the real API drift apart. Mitigation: the 3.0 DTOs are the single source; the TypeScript types come from the exported OpenAPI; if backend DTOs change in 3C, regenerate and fix compile errors before anything else.

---

## 4. Prompts

### 4.0 Message to paste into the **Layer 2 session** (so it cooperates)

```
Layer 3 is now running in parallel in another worktree. Please: (1) when step 2.5 (frontend workspace,
ui-kit, api-client, i18n setup) is committed, tell me the commit hash and run `git log --oneline -3`;
(2) after that commit, do not rename or remove existing ui-kit exports or change the api-client generation
script; additive changes only; (3) do not add Alembic migrations that are not needed for Layer 2;
(4) you remain the only session that edits the status table in CLAUDE.md. Continue with your plan.
```

### 4.1 Phase 3A prompt (new Layer 3 session, in the worktree)

```
Read CLAUDE.md, every file in docs/rules/, docs/design/DESIGN_SPEC.md, IMPLEMENTATION_PLAN.md section 8.3,
and PARALLEL_LAYER_3.md. Do not try to open any claude.ai link.

You are running in a git worktree on branch layer/3-customer-ui, created from main. Layer 2 is still in progress
in another session and is NOT merged. Do not touch Layer 2's merchant code, do not add Alembic migrations, and
do not edit the status table in CLAUDE.md. ADR numbers for this session start at 0020 (0012 is the
parallel-work ADR, 0013 to 0019 belong to the Layer 2 session). Use backend port 8001 and customer app port 5174.

GOAL: Phase 3A only. Build these three pieces, which need nothing from Layer 2:
 3.0 Customer API contract: Pydantic DTOs and router skeletons (returning clearly marked stub data from
     DESIGN_SPEC section 4, no database) for: customer session, budget, comfort check, plans, alternatives,
     consent, receipt. Follow docs/rules/api-conventions.md (camelCase, money in paise, problem+json,
     Idempotency-Key on consent). Do NOT mount these routers in api/dependencies.py or the app factory
     (Layer 2 is editing those); export the OpenAPI with a small separate script that mounts only the customer
     router. Mounting happens in Phase 3C.
 3.2 Comfort engine: ComfortRatio, ComfortBandClassificationStrategy with thresholds 35% and 50% in one
     configuration class labelled demo heuristics, and a synthetic profile provider behind a port
     (inflow Rs 30,000, existing EMIs Rs 8,000). Boundary tests at exactly 35% and 50%.
 3.3 Ranking and alternatives: PlanRankingStrategy with reason codes; "no plan fits" keeps all plans labelled
     above budget; alternatives (Rs 4,000 down payment, longer tenure, cheaper model) recomputed by the EMI
     engine. Check against the design sample numbers.
Same non-negotiable rules as always (CLAUDE.md section 2): all logic on the server, never hide a plan, exactly
three bands, no approved/declined wording.

PROCESS: plan mode, architect agent, show me the plan and WAIT for approval. Then backend-engineer step by
step, one commit per step, `make check` before each commit. STOP for my "continue" after 3.0 and after 3.3 with a
note of at most 15 lines. Write docs/handoff/LAYER-3-WIP.md (not LAYER-3-HANDOFF.md) and stop.
```

### 4.2 Sync point 1 (you, when Layer 2 commits step 2.5)

```bash
# in the Layer 3 worktree
git fetch
git rebase <commit-hash-of-step-2.5>      # replays Layer 3 commits on top of Layer 2's step 2.5
```

Resolve any conflicts (they should be limited to shared index files), run `make check`, then continue.

### 4.3 Phase 3B prompt (same Layer 3 session, or a fresh one)

```
Read CLAUDE.md, docs/rules/, docs/design/DESIGN_SPEC.md, docs/handoff/LAYER-3-WIP.md, PARALLEL_LAYER_3.md,
and the matching files in docs/design/mockups-source/ (C1 to C10, CustomerStates, TamilScreens, Components).
Layer 2 step 2.5 (ui-kit, api-client, i18n) is in this branch via rebase; Layer 2 is still unmerged.

GOAL: Phase 3B. Build apps/customer-web: the typed flow reducer (3.5) and screens C1 to C10 (3.6), in English and
Tamil, using only ui-kit tokens and the generated api-client types from the 3.0 contract.
Use a CustomerFlowApi interface with FixtureCustomerFlowApi (DESIGN_SPEC sample data) and HttpCustomerFlowApi,
chosen by a factory from an environment variable; default to the fixture for now. Never compute EMI, ratios or
bands in the UI. Add new files only; touch shared index files with one-line additions. Do not edit merchant-web.
Plan mode and my approval first; one commit per step; `make check` before each commit; STOP for my "continue"
after the flow reducer and after all screens exist. Update docs/handoff/LAYER-3-WIP.md and stop.
```

### 4.4 Sync point 2 (you, after Layer 2 is merged to main)

```bash
git fetch origin
git rebase --onto origin/main <commit-hash-of-step-2.5> layer/3-customer-ui
```

`--onto` replays only your Layer 3 commits onto `main`, which also works if Layer 2 was squash-merged. Then run `make migrate` and `make check`.

### 4.5 Phase 3C prompt (after sync point 2)

```
Read CLAUDE.md, docs/rules/, docs/design/DESIGN_SPEC.md, docs/handoff/LAYER-3-WIP.md,
the Layer 2 handoff (docs/handoff/LAYER-2-HANDOFF.md) and PARALLEL_LAYER_3.md. Layer 2 is merged and this branch
is rebased on main.

GOAL: Phase 3C. Build 3.1 customer sessions (QR token exchange bound to one sale), 3.4 consent and receipt
(OTP via a mock OTP port; append-only, hash-chained ConsentRecord storing the exact plan snapshot;
TemplateExplanationService; handoff trigger), replacing the 3.0 stub controllers with real services and
repositories, with ONE Alembic migration chain on top of Layer 2's. Then switch the customer app from the
fixture API to the real client (set the environment variable; keep the fixture implementation for tests).
Then 3.7: component and axe tests, Playwright full happy path (merchant starts a sale, customer completes
C1, C2, C3, C4, C6, C7, C9, C10) in English and Tamil, and the privacy test that merchant responses never
contain customer financial data. If the generated client disagrees with the backend DTOs, stop and tell me.

PROCESS: plan mode, architect agent, wait for approval; backend-engineer then frontend-engineer; one commit
per step; checkpoint for my "continue" after the backend and after the integration switch. At the end run the
reviewer agent, convert LAYER-3-WIP.md into docs/handoff/LAYER-3-HANDOFF.md, update the status table in
CLAUDE.md, print the summary and MR diff commands, then STOP and ask about Layer 4.
```

---

## 5. If it goes wrong

| Symptom | Fix |
|---|---|
| Rebase conflicts in `ui-kit/src/index.ts` or the router file | Keep both sides' lines; they are independent exports or registrations |
| Two Alembic heads | Stop. Merge Layer 2 first, then regenerate Layer 3's migration on top of it |
| Generated client no longer matches the stub contract | Regenerate from the real OpenAPI, fix TypeScript errors, update the fixture API |
| Layer 2 rewrites the 2.5 commits | Rebase again with `--onto` using the new hash; replay only Layer 3's commits |
| You cannot keep up with two review streams | Pause 3B; finish Layer 2 first. Quality over speed |

## 6. When not to do this

If Layer 2 is likely to finish within about an hour, parallel work saves little and adds rebasing and double review. Finish Layer 2, merge, then run Layer 3 straight through.

## 7. ADR text (also saved as `docs/adr/0012-parallel-layer-3.md` in this pack)

```
# 0012: Run Layer 3 in parallel with Layer 2

Status: accepted

## Context
Time is short for the event. Layer 3's pure domain code and the customer UI do not need Layer 2's backend.
Layer 1 is merged; Layer 2 is in progress at step 2.4.

## Decision
- Develop Layer 3 in a separate git worktree on branch `layer/3-customer-ui`, created from `main`.
- Phase 3A (customer API contract, comfort engine, ranking and alternatives) starts now from `main`.
- Phase 3B (customer UI against a fixture API) starts after Layer 2 step 2.5 is committed, by rebasing onto that commit.
- Phase 3C (customer sessions, consent and receipt, integration, tests) starts after Layer 2 is merged, by rebasing
  with `git rebase --onto origin/main <step-2.5-commit> layer/3-customer-ui`.
- Layer 3 merges only after Layer 2. No Alembic migrations in Layer 3 before the Layer 2 merge.
- Layer 3 routers are not mounted in the app until Phase 3C, to avoid conflicts in the composition root.
- ADR numbering: this ADR is 0012; the Layer 2 session uses 0013-0019; the Layer 3 session starts at 0020.
- Only the Layer 2 session edits the status table in CLAUDE.md; Layer 3 writes `docs/handoff/LAYER-3-WIP.md` until its own gate.

## Consequences
About 1.5 to 2.5 hours saved (estimate, not measured). Rebase work at two sync points, with small conflicts expected in
shared files. The fixture API and the real API may drift; controlled by the Phase 3A contract and a regenerated client.
The reviewer must watch for edits to Layer 2's files in Layer 3's diff.
```
