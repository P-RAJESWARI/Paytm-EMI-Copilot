# LAYER-4-HANDOFF: Sarvam AI integration

Branch `layer/4-sarvam-ai`, from `main` at `fee725c` (Layer 3 merged). Not pushed. Owner checkpoints were held after step 4.2 (the number audit) and step 4.5 (the LangGraph flows). From step 4.6 onwards the owner asked for **event mode** (about 1.5 hours): the backend and frontend were built in parallel, and some planned items were dropped (see "Not done"). All decisions are in [ADR 0023](../adr/0023-layer-4-sarvam-ai-number-audit-and-flows.md).

## What was built

**Customer screens:**
- **C2:** the microphone suggests a budget. The amount is always shown and confirmed by a tap. If the recording sounds misheard, the screen asks the customer to fix it or say it again.
- **C7:** a Listen button reads out exactly the text on screen. A "Written by AI…" note appears when the text came from the AI and passed the audit. Otherwise the standard text appears with no banner.
- **C8 teach-back:** an optional step, typed or spoken, between C7 and C9. It is advisory only and stores nothing.

**Merchant screens:** M5 and M8 show the AI-written weekly message with a "Written by AI from your shop's numbers" note when that language passed the audit.

**Backend (`backend/src/emi_copilot/`):**

| Piece | Where |
|---|---|
| Ports and labelled Mocks: `SpeechPort`, `ExplanationTextPort`, `AiFlowRunnerPort` | `adapters/ai/` |
| Sarvam adapters: `saaras:v4` speech-to-text, `bulbul:v3` text-to-speech, `sarvam-105b-conversations` chat. No retries, one breaker per capability, request keys from an allow-list | `adapters/ai/sarvam/` |
| Settings, modes (`off\|mock\|sarvam`) and a factory that fails fast without the key | `config/ai_settings.py`, `adapters/ai/factory.py` |
| **Number audit** (NFKC, Tamil digits, Indian and Western grouping, rupee markers, required mentions) and the wording guard | `domain/number_audit/` |
| Deterministic spoken-amount parser; teach-back scoring | `domain/speech/`, `domain/teach_back/` |
| Flows: explain → audit → choose; weekly message per language; teach-back | `services/ai/*_flow.py` |
| Sequential runner and LangGraph runner. The LangGraph runner is optional, linear, has a recursion limit and has no tools | `adapters/ai/flows/` |
| Decorators with template fallback; shown-text caches; one cost and latency log line per AI call | `services/ai/audited_*`, `services/ai/shown_explanation_cache.py`, `services/ai/ai_usage_logger.py` |
| Endpoints, rate limits, problem mappings | `api/controllers/customer_speech_controller.py`, `customer_teach_back_controller.py`, `api/ai_problem_mappings.py` |
| LangSmith tracing forced off at startup | `main.py` (`disable_third_party_ai_tracing`) |

**Endpoints** (`/api/v1`, customer endpoints use `X-Customer-Session-Token`):

New:
- `POST /customer-sessions/{id}/speech/transcriptions?purpose=BUDGET|TEACH_BACK` takes a raw audio body. It never changes the budget.
- `POST …/speech/synthesis` with `{explanationId}` returns audio with `no-store`.
- `POST …/teach-back` with `{offerId, answerText}`.

Additive changes:
- The explanation response gains `explanationId`, and its source can be `AI_AUDITED`.
- The customer session response gains `isVoiceAvailable`.
- The weekly message gains a `source` per language.

## Why (decisions)
These are in ADR 0023. The owner approved the plan's 13 defaults; the main decisions are:
- **The audit lives in the domain** (`backend.md` §1 updated). Magnitude words fail the audit, and the monthly and extra amounts must both be mentioned.
- **Prompts carry plan figures only**, never the band, ratio, income, EMIs or budget.
- **Teach-back never sends the customer's words to the LLM.**
- **langchain-core is accepted only as a transitive dependency**, with a lint ban on importing it.
- **Logs replace a tracing port.** Each AI call writes one cost and latency line.
- **Text-to-speech is returned as binary audio.**
- **M8 Listen is deferred.**

**Live smoke check, 15 Nov.** I ran a manual script with synthetic data; it is not in CI.
- `sarvam-105b` spent its whole token budget on hidden reasoning. With 600 or 2,000 max tokens it returned an empty answer. With 4,000 tokens it took 6.3 s, over the 6 s timeout.
- The AI text therefore always fell back to the template. The audit and fallback did their job.
- `sarvam-105b-conversations` answered in 0.3 s, so it is now the default. It is the same 105B family the owner chose.
- Speech-to-text returns amounts as words ("three thousand six hundred and sixty seven"), so the parser now reads compound number words.

## Patterns used
| Pattern | File | Problem solved |
|---|---|---|
| Port and Adapter | `adapters/ai/speech_port.py`, `explanation_text_port.py`, `flows/flow_runner_port.py` | Vendor and runtime are swappable; tests need no network |
| Adapter | `adapters/ai/sarvam/*`, `flows/langgraph_flow_runner.py` | Vendor shapes and errors stay at the boundary |
| Factory | `adapters/ai/factory.py` | Mode choice, failing fast, announcing Mocks |
| Decorator | `services/ai/audited_explanation_service.py`, `audited_weekly_message_writer.py` | Audit and fallback without touching adapters |
| Template fallback | `services/customer/template_explanation_service.py`, `domain/reports/weekly_message_template.py` | A safe text is always available |
| Strategy | `domain/teach_back/teach_back_scoring_strategy.py`; the sequential and LangGraph runners | Swappable scoring and runtime |
| Value Object | `domain/number_audit/allowed_numbers.py` | Audit inputs cannot be invalid |
| Circuit Breaker | one breaker per Sarvam capability through `core/resilient_http_client.py` | A slow capability cannot block the others |
| Finite state machine (UI) | the `teachBack` step in `customer-flow/model/` | C8 is optional, and consent stays gated |

## How to run and verify
```bash
make check                       # lint, mypy strict, backend and frontend tests, coverage gates, core-without-langgraph
make openapi-check
make core-without-langgraph      # app plus an explanation, with langgraph and langchain imports blocked
make dev                         # Mock AI by default; for live AI:
SPEECH_PROVIDER_MODE=sarvam EXPLANATION_TEXT_PROVIDER_MODE=sarvam AI_FLOW_RUNNER=langgraph make dev
MOCK_AI_TEXT_BEHAVIOUR=wrong_number make dev   # C7 shows the template text: the audit fallback, offline
```

Show the audit:
- Unit test: `uv run pytest -v -k one_wrong_digit tests/unit/domain/number_audit`
- End to end: `tests/unit/services/ai/test_audited_explanation_service.py::test_audited_explanation_service_ai_text_with_wrong_digit_returns_template_text`

## What to review first
1. `domain/number_audit/number_audit_service.py` and `number_token_extractor.py`: the safety control.
2. `services/ai/audited_explanation_service.py` and `explanation_flow.py`: no AI exception or unaudited text escapes.
3. `adapters/ai/sarvam/sarvam_chat_text_adapter.py`: the request key allow-list (no `tools`); only `content` is read.
4. `services/ai/explanation_prompt_builder.py` and `adapters/ai/prompt_facts.py`: what the model sees. A privacy test covers it.
5. `api/controllers/customer_speech_controller.py`: raw audio body, size limit, no storage, no budget change.
6. Frontend: `features/voice/hooks/useVoiceRecorder.ts` (tracks stopped, recording dropped) and `features/explanation/` (no banner on failure).

**MR size:** about 11,500 changed lines (4,900 of them tests), excluding lockfiles, `openapi.json` and the generated client. That is far above the ~1,500-line guide. Review it in commit groups:
- A. Domain and adapters: `1f5670b`..`75aa2e1`
- B. Wiring and API: `8b36ce7`, `ec49ecb`, the model and spoken-amount fix `7021fd7`, and the review fix `bd3813d` (any unexpected AI flow error falls back to the template)
- C. Frontend: `9f93a79`..`d8f0168`
- D. Documents and gate fixes

**Over the soft limits:**
- `api/dependencies.py` is 308 lines. The composition root holds the AI caches and the AI rate limiter.
- `customer-web/.../FixtureCustomerFlowApi.ts` is 318 lines. The fixture adapter implements every port method. A follow-up can move the voice methods next to `fixtureVoiceData.ts`.

Earlier over-limit files are listed in the Layer 3 handoff.

## Test and coverage results
- **Backend:** 3,480 tests pass. Coverage is about 99% overall; domain, core and adapters are at 100%, services at 99%.
- **Frontend:** 533 Vitest tests pass in 72 files, with axe on every new state. Coverage is about 98% statements. The customer flow reducer is at 100%.
- **Gates:** ruff, `mypy --strict` and detect-secrets are clean. `make openapi-check` is in sync, and `make core-without-langgraph` passes.
- **Live smoke check** (manual, synthetic data): speech-to-text, text-to-speech and chat (conversations model) all work against the real Sarvam API.

## Known limitations and mocks
- **Unverified Sarvam details, marked [Verify]:**
  - the price of the conversations model (cost logs estimate it with the 105b prices)
  - the Tamil voice (`shubh`)
  - whether one auth header alone is enough (we send both)
- **The audit checks values, not their roles.** If two allowed numbers swap places, the audit cannot catch it. Required mentions and short prompts reduce this risk.
- **Spoken amounts:** "three thousand or four" reads as ₹3,004 because "or" is dropped. The customer always confirms the amount on screen.
- **Tamil:** compound spoken amounts are read in English only. Tamil reads single magnitudes such as "மூன்று ஆயிரம்". All Tamil copy is draft (see the [checklist](../review/TAMIL_COPY_REVIEW_CHECKLIST.md)).
- **Caches and rate limiters are in memory**, so the backend must run as one worker.
- **"Send" on the weekly message renders the text again through the cache**, which keeps entries for 12 hours. If the cache entry expired, or the report facts changed between viewing and sending, a newly audited AI text (or the template) is sent instead of the one shown. A follow-up is to send the fingerprint of the shown text with the request.
- **The English weekly template contains "one" and "first"**, which the audit rejects. The template is the fallback and is not audited, so nothing breaks. AI text that copies those words falls back.

## Not done / follow-ups (dropped in event mode)
- Migration 0007 with the `AI_TEXT_FALLBACK_USED` and `AI_NUMBER_AUDIT_FAILED` audit events. Today the fallback is visible only in the cost log line.
- `AiTracingPort` with OpenTelemetry or Langfuse.
- Golden tests beyond the wrong-digit, paise, missing-extra and forbidden-word cases.
- The Playwright AI-down spec. The Layer 3 e2e specs run on the Mock.
- M8 Listen (needs a merchant text-to-speech endpoint).
- A scripted check of the customer bundle size.
- Moving `transcribeSpeech` onto the typed client: the schema types the raw body as a string.

## Open questions
1. Keep `sarvam-105b-conversations` as the default text model, or go back to `sarvam-105b` with a larger budget and a longer timeout (about 6 s or more and about 700 tokens per explanation)?
2. Who reviews the Tamil strings and listens to the Tamil voice (Q13)?
3. Are the AI audit events (migration 0007) wanted before any pilot?
