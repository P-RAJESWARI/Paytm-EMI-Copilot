# PROMPTS.md: Copy-paste prompts for Claude Code, one set per phase

## 0. How this works (read once)

**Do the prompts build the whole project in one go? No, and they should not.** One prompt cannot reliably build everything: the context window fills up, mistakes compound, and you would learn nothing. Instead:

- There are **four layer prompts** (one per layer) and **four reusable helper prompts** (continue, resume, review gate, fix review feedback).
- Each layer prompt makes Claude Code work through many steps by itself, but it **stops at set checkpoints** and waits for you. That is where you read, ask questions and approve.
- Rules, design and decisions are **in files** (`CLAUDE.md`, `docs/rules/`, `docs/design/`, `docs/handoff/`), so a brand-new session loses nothing.

**Your control points in every layer**

| # | Checkpoint | What you do |
|---|---|---|
| 1 | Plan approval (before any code) | Read the plan, answer questions, say "approved" |
| 2 | Mid-layer checkpoint (one or two per layer) | Read the What / Why / Review note, run `git log`, say "continue" |
| 3 | Layer gate (end) | Read the summary and MR diff, review, say "continue to Layer N+1" |

**Can Claude Code read the Claude design artifact? Do not rely on it.** The design link is a private claude.ai page, and Claude Code runs in your terminal without your claude.ai login, so it will most likely not be able to open it **[Inferred; I could not test Claude Code from here]**. That is why the pack already contains the design in readable form: `docs/design/DESIGN_SPEC.md` (requirements and sample data) and `docs/design/mockups-source/` (the screen files, including the English and Tamil strings). The prompts tell Claude Code to use those and not the link. For extra safety, export screenshots of each screen from the design and put them in `docs/design/screenshots/`; Claude Code can read images placed in the project.

---

## 1. One-time setup (you, in a terminal)

```bash
mkdir emi-copilot && cd emi-copilot
git init -b main
# copy the contents of emi-copilot-docs/ into this folder (CLAUDE.md, IMPLEMENTATION_PLAN.md,
# PROMPTS.md, docs/, .claude/), then:
git add . && git commit -m "docs(rules): add project rules, design spec and agent definitions"
claude        # start Claude Code in this folder
```

**Quick check prompt (optional, paste first):**

```
Read CLAUDE.md. Then list: (1) the non-negotiable rules, (2) the four layers and their branches,
(3) the decisions already made in section 4a, (4) the agents available. Do not write any code.
If anything in the docs contradicts itself, tell me.
```

Expected: Claude Code summarises the ten rules, says Python, no Paytm keys (Mock default), and lists the four agents. If it cannot see the agents, check that the `.claude/agents/` folder was copied.

---

## 2. Layer prompts

### Layer 1: Foundation + Payment gateway integration (new session S1)

```
Read CLAUDE.md, every file in docs/rules/, docs/design/DESIGN_SPEC.md, and IMPLEMENTATION_PLAN.md section 8.1.
Do not try to open any claude.ai link; the design is in docs/design/.

GOAL: build Layer 1 (Foundation + Payment gateway integration) on a new branch layer/1-payment-gateway.

DECISIONS ALREADY MADE (do not re-ask): Python 3.12 + FastAPI. We have NO Paytm credentials, so the Mock
payment gateway adapter is the default and the real Paytm adapter is built and tested against recorded
fixtures only; it activates only with PAYMENT_GATEWAY_MODE=paytm plus credentials. LangGraph is not used in this layer.

PAYTM API RULES: use only endpoints and fields you can confirm in Paytm's current public documentation
(paytmpayments.com/docs and business.paytm.com/docs). If you cannot reach the docs or are unsure of a field,
STOP and ask me. Never invent an endpoint. Mark every unverified detail with [Verify] in a comment and in the handoff file.

PROCESS:
1. Start in plan mode. Run the architect agent. Show me the plan, patterns, and numbered questions. WAIT for my approval.
2. After approval, delegate to the backend-engineer agent one step at a time (steps 1.0 to 1.9 in the plan).
   Give it the goal, the files to read, and the acceptance criteria each time. One commit per step in the
   format from docs/rules/git-workflow.md, with What / Why / Review lines. Run `make check` before every commit.
3. CHECKPOINTS: stop and wait for my "continue" after step 1.3 (domain + persistence) and after step 1.7
   (adapters). At each checkpoint write a note of at most 15 lines: what was built, why, patterns used,
   what I should read first, and the test results.
4. If a decision is missing or two documents disagree, stop and ask. Record answers in docs/adr/.
5. At the end: run the reviewer agent and fix blocking issues, write docs/handoff/LAYER-1-HANDOFF.md,
   update the layer status table in CLAUDE.md, print the layer summary and the MR diff commands,
   then STOP and ask whether to continue to Layer 2. Never continue on silence.
```

**You review at checkpoint 1.3:** `Money` has no floats; EMI results match ₹3,667 x 6, ₹3,850 x 6, ₹2,050 x 12 on ₹22,000; `audit_event` has no update or delete path.  
**You review at checkpoint 1.7:** the port uses domain words (no Paytm field names); create-link calls are never retried; the Mock is the default and announced at startup.

### Layer 2: Merchant UI + merchant backend slice (new session S2)

Start only after the Layer 1 MR is merged to `main`.

```
Read CLAUDE.md, every file in docs/rules/, docs/design/DESIGN_SPEC.md, the latest file in docs/handoff/,
and IMPLEMENTATION_PLAN.md section 8.2. Do not try to open any claude.ai link. For layout, states and the
English and Tamil strings, open the matching files in docs/design/mockups-source/ (M1 to M5, M8, Main, Components,
MerchantStates, M3Phone). If there are screenshots in docs/design/screenshots/, look at them too.

GOAL: build Layer 2 (Merchant UI + merchant backend slice) on a new branch layer/2-merchant-ui, branched from the latest main.

DECISIONS ALREADY MADE: Python backend. Mock payment gateway is still the default. Pairing PINs: no owner app;
create a seed command that creates the demo merchant "Ravi Electronics" (Shop ID RAVI-0193) and a demo PIN, using
the sample data in DESIGN_SPEC section 4. "Share with brand rep" copies a text summary to the clipboard (no sending).
The weekly message is built from a template now and shown as sent by marking it sent in the database (no real
WhatsApp or SMS); the AI version comes in Layer 4. Frontend is a pnpm monorepo with apps/merchant-web,
apps/customer-web (empty until Layer 3), and packages ui-kit, api-client, shared-i18n.

NON-NEGOTIABLE: merchant APIs and screens must never expose customer income, existing EMIs, comfort ratios or
step-by-step progress; only CHOOSING or READY_TO_PAY, the chosen plan and totals, and aggregates. Add a test that
asserts the exact response schemas.

PROCESS:
1. Plan mode. Run the architect agent. Show the plan, patterns, and numbered questions. WAIT for my approval.
2. Delegate steps 2.1 to 2.4 to backend-engineer, then 2.5 to 2.7 to frontend-engineer (goal, files, acceptance
   criteria each time). One commit per step, format from git-workflow.md, `make check` before every commit.
3. CHECKPOINTS: stop for my "continue" after step 2.4 (backend slice complete; show me the OpenAPI summary) and
   after step 2.6 (screens built). Each checkpoint: a note of at most 15 lines (what, why, patterns, what to read
   first, test results), plus how I can run and look at it.
4. Ask me if anything is ambiguous, including any difference between the spec and a mockup.
5. At the end: reviewer agent, fix blocking issues, write docs/handoff/LAYER-2-HANDOFF.md, update the status table
   in CLAUDE.md, print the layer summary and MR diff commands, then STOP and ask whether to continue to Layer 3.
```

### Layer 3: Customer UI + customer backend slice (new session S3)

Start only after the Layer 2 MR is merged.

```
Read CLAUDE.md, every file in docs/rules/, docs/design/DESIGN_SPEC.md, the latest file in docs/handoff/,
and IMPLEMENTATION_PLAN.md section 8.3. Do not try to open any claude.ai link. For layout, states and strings use
docs/design/mockups-source/ (C1 to C10, CustomerStates, TamilScreens, Components, Main) and any screenshots.

GOAL: build Layer 3 (Customer UI + customer backend slice) on a new branch layer/3-customer-ui, branched from the latest main.

DECISIONS ALREADY MADE: Python backend; Mock gateway default; comfort check uses a synthetic profile behind a port
(inflow Rs 30,000, existing EMIs Rs 8,000, as in DESIGN_SPEC); band thresholds 35% and 50% live in one configuration
class and are labelled demo heuristics; OTP uses a mock OTP port; the cooling-off wording is a placeholder; Tamil
strings are drafts marked "needs native review"; explanations use TemplateExplanationService now (AI comes in Layer 4).

NON-NEGOTIABLE: all EMI, extra-cost, ratio, band, ranking and alternative logic stays on the server; the UI only
displays it. Never hide a plan. Exactly three bands (Comfortable, Stretching, Risky) with icon and word. No
"approved/declined" wording. Consent rows are append-only and hash-chained and store the exact plan shown.

PROCESS:
1. Plan mode. Run the architect agent. Show plan, patterns, numbered questions. WAIT for my approval.
2. Delegate steps 3.1 to 3.4 to backend-engineer, then 3.5 to 3.7 to frontend-engineer. One commit per step,
   `make check` before every commit.
3. CHECKPOINTS: stop for my "continue" after step 3.4 (backend slice: show boundary tests at exactly 35% and 50%
   and the consent hash-chain test) and after step 3.6 (all screens C1 to C10 built).
4. Ask me about any ambiguity or spec-versus-mockup difference.
5. At the end: reviewer agent, fix blocking issues, write docs/handoff/LAYER-3-HANDOFF.md, update CLAUDE.md status,
   print the layer summary and MR diff commands, then STOP and ask whether to continue to Layer 4.
```

### Layer 4: Sarvam AI integration (new session S4)

Start only after the Layer 3 MR is merged. Have your Sarvam API key ready.

```
Read CLAUDE.md, every file in docs/rules/, docs/design/DESIGN_SPEC.md, the latest file in docs/handoff/,
and IMPLEMENTATION_PLAN.md section 8.4. Do not try to open any claude.ai link.

GOAL: build Layer 4 (Sarvam AI integration) on a new branch layer/4-sarvam-ai, branched from the latest main.

DECISIONS ALREADY MADE: LangGraph is used ONLY for the AI flows in this layer (explain then audit then fallback;
teach-back scoring, advisory only; weekly merchant message then audit). No cycles, no tool-calling nodes, set a
recursion limit. The deterministic core must still run and be tested without LangGraph installed. No LangChain.
The Sarvam API key is in .env as SARVAM_API_KEY (never commit it).

FIRST, BEFORE PLANNING, ASK ME: which model should write the explanation text? (Sarvam text model if my credits
cover it, otherwise another hosted model behind the same port.) Also check Sarvam's CURRENT public API
documentation online for the speech-to-text and text-to-speech request shapes and model names. If you cannot
reach the docs, stop and ask me. Mark unverified details [Verify]. Never invent an endpoint or parameter.

NON-NEGOTIABLE: AI has no tools and no database or payment access. It receives structured plans and reason codes
only, never names, phone numbers or account data. Every number in AI text passes the NumberAuditService; any
mismatch falls back to the template text. Voice audio is never stored. With AI disabled every screen still works
with standard text and no error banner. Every spoken number is also on screen.

PROCESS:
1. Plan mode. Run the architect agent. Show plan, patterns, numbered questions. WAIT for my approval.
2. Delegate steps 4.1 to 4.6 to backend-engineer and step 4.7 to frontend-engineer, step 4.8 tests to both.
   One commit per step, `make check` before every commit. No live network calls in tests or CI.
3. CHECKPOINTS: stop for my "continue" after step 4.2 (number audit; show the wrong-digit fallback test),
   after step 4.5 (LangGraph flows), and at the gate.
4. At the end: reviewer agent, fix blocking issues, write docs/handoff/LAYER-4-HANDOFF.md, update CLAUDE.md status,
   update the README with an architecture diagram and the honest-limits section, print the layer summary and
   MR diff commands, then STOP.
```

---

## 3. Helper prompts (reuse in any layer)

**Continue after a checkpoint**

```
Continue with the next steps of the current layer exactly as planned. Same rules: one commit per step,
`make check` before every commit, stop at the next checkpoint with a note of at most 15 lines.
```

**Resume in a fresh session** (context ran out, or you came back later)

```
Read CLAUDE.md, every file in docs/rules/, docs/design/DESIGN_SPEC.md and the latest file in docs/handoff/.
Run `git status` and `git log --oneline -15` and tell me which layer and which step we are on, what is done,
and what remains. Do not write code until I confirm.
```

**Run the review gate manually**

```
Run the reviewer agent on the current branch against origin/main. Show its verdict. Then show me:
git diff --stat origin/main...HEAD and git log --oneline origin/main..HEAD.
List the five files I should read first and what to look for in each. Do not change any code.
```

**Fix my review feedback**

```
Here is my review feedback:
<paste your comments here>
For each comment: say whether you agree, make the smallest change that fixes it, add or adjust a test, and
commit with the format from git-workflow.md. Do not rewrite unrelated code. Run `make check`, then show me a
list of comment-to-commit mappings.
```

**Explain something so I learn it**

```
Explain <file or concept> as if I am a mentor reviewing it: what problem it solves, which design pattern it uses
and why that pattern, what would break without it, and one alternative you rejected. Use the real code from this
repo. Keep it under 25 lines.
```

---

## 4. Event mode add-on (Sunday only)

Paste this **after** any layer prompt if time is short:

```
EVENT MODE: time is limited. Keep every rule in CLAUDE.md section 2. Keep the tests for money maths, the number
audit and consent. Shorten reviews: skip the long checkpoint notes (5 lines maximum) and run the reviewer agent
once at the end of the layer instead of at every checkpoint. Build the happy path first: customer screens
C1, C2, C4, C7, C9, C10 and merchant screens M1 to M5. Leave C5, C6 and C8 as clearly marked follow-ups unless
time remains. Tell me what you skipped in the handoff file.
```

---

## 5. Practical tips

- **Answer Claude Code's questions in the same session.** It records decisions in `docs/adr/`, which later sessions read.
- **Do not skip the plan approval.** It is the cheapest place to catch a wrong assumption.
- **Merge each layer's MR before starting the next session.** Each layer branches from the latest `main`.
- **If Claude Code proposes something that breaks a rule in `CLAUDE.md` section 2, say no.** The rules win over convenience.
- **Never paste real Paytm or Sarvam keys into a prompt.** Put them in `.env`.
- **Details of Claude Code commands and features can change.** If a command in this pack does not work in your version, check the current Claude Code documentation.
