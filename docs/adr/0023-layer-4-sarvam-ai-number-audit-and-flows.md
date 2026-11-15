# 0023: Layer 4 AI — Sarvam provider, number audit, LangGraph flows, voice handling

Status: Accepted. The owner approved the Layer 4 plan and its 13 default answers on 2026-11-15. The owner then asked for event mode, which dropped some planned items (see "Dropped in event mode"). This one ADR replaces the six planned (0023 to 0028), to save time on the event day.

## Context
Layer 4 adds three things:
- AI-written explanations and the AI-written weekly merchant message
- speech-to-text for the budget and teach-back
- text-to-speech for C7

CLAUDE.md rules 1 and 2 keep AI out of the money path, and require every AI number to be verified against the engine's output, with the template text as the fallback.

## Decisions

### 1. Provider (owner)
Sarvam provides all three AI functions:

| Function | Model | Endpoint |
|---|---|---|
| Speech-to-text | `saaras:v4` | `POST /speech-to-text`, multipart |
| Text-to-speech | `bulbul:v3`, mp3 | `POST /text-to-speech`, JSON |
| Text | `sarvam-105b-conversations` (the owner chose the 105B family) | `POST /v1/chat/completions` |

**Model change after the live check on 2026-11-15.** `sarvam-105b` spent its whole token budget on hidden reasoning. With 600 or 2,000 max tokens it returned an empty answer with `finish_reason` `length`. With 4,000 tokens it took 6.3 s, which is over the 6 s timeout. `sarvam-105b-conversations` answered in 0.3 s with about 25 tokens, so it is the default. `SARVAM_CHAT_MODEL` can switch back. `reasoning_effort` accepts only low, medium or high.

- The request shapes were checked against docs.sarvam.ai on 2026-11-15. Fixtures in `backend/tests/contract/fixtures/sarvam/` follow the documented shapes and are marked [Verify].
- Chat auth sends both `api-subscription-key` and `Authorization: Bearer`, because the docs list both [Verify].
- Text calls send only `model`, `messages`, `temperature`, `max_tokens`, `reasoning_effort` and `n`, from an allow-list. `tools` can never be sent.
- Only `finish_reason == "stop"` is accepted.

### 2. Modes and failing fast
- `SPEECH_PROVIDER_MODE` and `EXPLANATION_TEXT_PROVIDER_MODE` each take `off`, `mock` or `sarvam`, default `mock`.
- `sarvam` without `SARVAM_API_KEY` refuses to start (the ADR 0004 style). Mocks and `off` are announced in the startup log.
- The `api-subscription-key` header is redacted from logs.
- The tests clear all AI settings from the environment, so a developer's `.env` cannot reach pytest.

### 3. Number audit (`domain/number_audit/`, owner questions 1, 4 and 5)
The audit is in `domain/number_audit/`, not `adapters/ai/` as `backend.md` §1 first said, because services may import only ports. `backend.md` is updated to match.

**Normalisation:**
- Text is NFKC-normalised, and Tamil and other Unicode digits become ASCII.
- ₹, Rs and INR prefixes and rupee suffixes mark rupee amounts.
- Plain, Western and Indian digit grouping are treated as equal.
- `.00` equals the whole number.

**Mismatches.** Any of these makes the text fall back to the template:
- an amount the engine did not produce
- malformed grouping
- a paise fraction (ADR 0001: shown values are whole rupees)
- a magnitude word or `%`
- an ordinal or a stray number word (for example "one" or "first")
- empty text
- the monthly amount or the extra in total is missing
- forbidden wording: approve or decline words, eligibility, interest rate, best or recommended, urgency, or the band words

**What each text may contain:**
- The explanation may use the monthly amount, the extra, the total, the price, the tenure and digits in the labels.
- The weekly message may use counts that are not suppressed (counts from 1 to 4 never reach the AI), money amounts, dates and digits in product names.

The English weekly template itself says "One thing to do" and "first payment", which the audit rejects. The template is the fallback and is never audited. The prompt tells the model not to use number words or ordinals.

### 4. What prompts contain (owner question 3)
- Prompts contain only typed plan facts: the plan kind, name, lender or funder, tenure, and the shown monthly, extra, total and price.
- They never contain names, phone numbers, income, existing EMIs, the ratio, the band, the budget or any IDs. Tests check the exact key sets.
- The facts block is marked as data, not instructions, and product names are treated as untrusted.

### 5. Flows and LangGraph (owner questions 6 and 7)
- **`AiFlowRunnerPort`** has two implementations: `SequentialAiFlowRunner`, which is the default, and `LangGraphAiFlowRunner`, which comes with the optional `ai` extra (`langgraph==1.2.19`).
- **The LangGraph runner's limits:**
  - Graphs are linear, with no cycles, no tool nodes and no prebuilt agents.
  - `recursion_limit = steps + 1`, capped at 6.
  - A flow therefore has at most 5 steps.
- **Imports are restricted:**
  - Only `langgraph_flow_runner.py` imports `langgraph`.
  - Ruff `TID251` bans `langchain*` imports everywhere.
  - `langchain-core` is accepted as a transitive dependency only.
- **Lock constraint:** `langsmith<0.12` is pinned so `httpx2` is not pulled in. `httpx2` would switch Starlette's TestClient and break the Layer 1–3 tests.
- **LangSmith tracing is forced off at startup.**
- **`make core-without-langgraph`** is part of `make check`. With langgraph blocked from importing, it builds the app and runs an explanation.
- **Teach-back is deterministic and advisory.** The customer's words never reach the LLM. `CLOSE_ENOUGH` means the tenure is exact and the monthly amount is within 5% [Verify heuristic]. Nothing is stored.

### 6. Decorator and caches (owner question 8)
- `AuditedExplanationService` wraps the AI explainer and falls back to `TemplateExplanationService`. Weekly message rendering goes through the same flow, one language at a time.
- In-memory caches, bounded and with a time limit, keep the shown text stable across repeat reads. Text-to-speech speaks exactly the cached text, identified by `explanationId`, and "send" delivers exactly the weekly text that was shown.
- One worker only, as in Layers 2 and 3.

### 7. Voice
- Audio is uploaded as a raw `audio/*` body of at most 512 KiB (`python-multipart` is not needed) and kept only in memory. It is never written to disk or logged.
- A transcript never changes the budget. A deterministic `SpokenAmountParser` suggests an amount, and the customer confirms it on screen.
- Text-to-speech returns audio bytes with `Cache-Control: no-store`.

### 8. Cost and latency (owner question 9)
- Each AI call writes one structured log line: the flow, model, latency, input and output usage counts, estimated INR cost (a `Decimal` from settings prices, [Verify]) and the outcome.
- Prompt, completion and transcript text are never logged.

## Dropped in event mode (owner, 2026-11-15)
- Migration 0007 with the `AI_TEXT_FALLBACK_USED` and `AI_NUMBER_AUDIT_FAILED` audit events. Fallbacks are visible in the cost log line's outcome, not in `audit_event`.
- `AiTracingPort`, OpenTelemetry and Langfuse.
- The broader golden-test set and the Playwright AI-down specification.
- The M8 Listen button.

These are follow-ups in `LAYER-4-HANDOFF.md`.

## Consequences
- With AI off, slow or failing the audit, every screen shows the standard text with no banner.
- The audit checks that values are allowed, not which role each value plays. If two allowed numbers swap places, the audit cannot catch it. The required mentions and short prompts reduce this risk.
