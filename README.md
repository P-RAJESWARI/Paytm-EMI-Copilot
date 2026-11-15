# EMI-at-Counter Copilot

Paytm makes EMI available. This product makes it affordable and understood, and shows merchants why they lose sales.

A shopkeeper starts a sale on a tablet. The customer scans a QR code on their own phone and:
- says what they can comfortably pay each month
- compares EMI plans by **monthly amount and extra cost in total** side by side
- can run an optional, consented comfort check
- hears or reads a plain Tamil or English explanation
- consents with an OTP and is handed off to Paytm to pay

The merchant gets a sales report with the funnel, missed sales, money due from brands and a weekly message.

Built for the Paytm Build for India AI Hackathon, Chennai, Track 2. Project rules are in [CLAUDE.md](CLAUDE.md) and [docs/rules/](docs/rules/). Each layer's handoff is in [docs/handoff/](docs/handoff/).

## Architecture

```
 merchant-web (tablet PWA)           customer-web (phone PWA, opened by QR)
   M1 pair · M2 new sale · M3 QR       C1 welcome · C2 budget (type or speak) · C3 comfort consent
   M4 handoff · M5/M8 report+message   C4 plans · C5 detail · C6 alternatives · C7 explanation (listen)
                 \                     C8 teach-back (optional) · C9 OTP consent · C10 receipt
                  \                   /
                   REST /api/v1 · camelCase JSON · money as integer paise · problem+json errors
                                      |
 FastAPI backend (Python 3.12) ───────┴──────────────────────────────────────────────────────────
   api/controllers ──> services ──> repositories ──> PostgreSQL 16
                          │            (sales, consent_record hash chain, audit_event, reports)
                          │
                          ├──> domain  (pure; no I/O)
                          │      Money · EMI engine · comfort bands · ranking · alternatives
                          │      number_audit · spoken_amount_parser · teach_back scoring
                          │
                          ├──> adapters (ports + Mock and real implementations)
                          │      payment_gateway: Mock | Paytm          (D2: Mock until staging keys)
                          │      settlement, customer_contact, consent_otp, financial_profile: Mock
                          │      ai/  SpeechPort ─────── Mock | Sarvam saaras:v4 (STT), bulbul:v3 (TTS)
                          │           ExplanationTextPort ─ Mock | Sarvam sarvam-105b (chat)
                          │           AiFlowRunnerPort ─── Sequential | LangGraph (optional extra)
                          │
                          └──> events (Observer: audit, funnel, merchant live status via SSE)
```

**How AI is kept out of the money path:**
```
 engine figures ──> prompt facts (plan figures only) ──> AI text ──> NumberAuditService ──┐
        │                                                                                 │ pass: AI_AUDITED
        └──────────────────────────> TemplateExplanationService (standard text) <─────────┘ fail / down: TEMPLATE
```
- AI writes only words. The deterministic code calculates every EMI, total, ratio and band, and every ranking.
- Every number in AI text must match the engine's output, or the template text is shown instead.
- AI components have no tools and no database or payment access. Prompts never contain names, phone numbers, income, existing EMIs, ratios or bands.
- Speech is optional. A spoken budget is always shown on screen and confirmed with a tap. Text-to-speech reads only the exact text already on screen.
- LangGraph runs only the small AI flows: explain, then audit, then fall back; advisory teach-back; the weekly message. The graphs are linear, with no cycles, no tool nodes and a recursion limit. The core runs and is tested without LangGraph (`make core-without-langgraph`).

## Run it

Needs Docker, [uv](https://docs.astral.sh/uv/), Node 20 and pnpm.

```bash
cp .env.example .env            # then set DEMO_MERCHANT_PIN (6 digits) and, for real AI, SARVAM_API_KEY
make setup frontend-setup       # Python (with the `ai` extra) and frontend dependencies, pre-commit hooks
make seed                       # demo shop RAVI-0193 with products and report history
make dev                        # API on http://127.0.0.1:8000 (auto-reload)
pnpm --dir frontend --filter @emi-copilot/merchant-web dev    # http://localhost:5173
CUSTOMER_WEB_API_PROXY_TARGET=http://127.0.0.1:8000 \
  pnpm --dir frontend --filter @emi-copilot/customer-web dev  # http://localhost:5174
```

Pair the tablet with shop `RAVI-0193` and your PIN, then start a sale and open the QR link. The Mock consent OTP is `123456`.

**AI modes** are set in `.env`, and the default is `mock`:

| Variable | Values | Effect |
|---|---|---|
| `EXPLANATION_TEXT_PROVIDER_MODE` | `off` · `mock` · `sarvam` | Who writes the C7 explanation and the weekly message |
| `SPEECH_PROVIDER_MODE` | `off` · `mock` · `sarvam` | Microphone and Listen; `off` hides them |
| `AI_FLOW_RUNNER` | `sequential` · `langgraph` | The runtime for the AI flows; both give identical results |
| `MOCK_AI_TEXT_BEHAVIOUR` | `correct` · `wrong_number` · `unavailable` | Demonstrates the audit fallback with no network |

`sarvam` mode refuses to start without `SARVAM_API_KEY`. Every Mock adapter announces itself in the startup log.

**Checks:** `make check` runs lint, mypy strict, backend and frontend tests, the coverage gates and the no-LangGraph check. `make openapi-check` checks that the API client matches the backend. `make e2e` runs Playwright.

## Honest limits

This is a hackathon build. These parts are **mocked, synthetic or unverified**:

- **No real lending decision.** The comfort check is advice, not a credit decision. Its bands (Comfortable, Stretching, Risky) use demo thresholds of 35% and 50% that a lender or risk team must confirm.
- **Financial data is synthetic.** Income and existing EMIs come from a Mock profile, not an account aggregator.
- **Payments are simulated by default.** The Paytm adapter is built against documented request shapes, but no staging keys were available. Settlement batches ("money due from brands") are synthetic.
- **The customer's phone number and the OTP are mocked.** The OTP is a fixed demo code. No SMS is sent.
- **AI text can be wrong**, which is why it is audited. The audit checks that every number is an engine figure, not that each number sits in the right place. Short prompts, required mentions and a ban on decision words reduce, but do not remove, that risk. When AI is off, slow or fails the audit, the standard text is shown with no error banner.
- **Sarvam API details are marked [Verify]** where the public docs were unclear: the chat auth header, `reasoning_effort` and finish-reason values, the error body shapes, the voice used for Tamil, and the prices used for cost logging.
- **Voice audio is never stored.** It is held in memory for one call to Sarvam and discarded.
- **Tamil text is a draft** until a native speaker reviews it (see [docs/review/TAMIL_COPY_REVIEW_CHECKLIST.md](docs/review/TAMIL_COPY_REVIEW_CHECKLIST.md)).
- **The cooling-off period wording is a placeholder** until the lender confirms the period.
- **Run one worker only.** Rate limiters and the shown-text caches are in memory and per process.
- **No Paytm logos or assets** are used.
