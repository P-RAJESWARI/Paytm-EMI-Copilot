# testing.md: Testing rules

## 1. Principles

- Tests are part of the deliverable, not an afterthought. Every behaviour added has a test in the same commit or before it.
- Money maths and the number audit are the highest-risk code. They get property-based tests and the strictest thresholds.
- **No live network calls in tests or CI.** External services (Paytm, Sarvam, LLM) are replaced by Mock adapters or recorded fixtures.
- Tests read like documentation: a mentor should understand the behaviour from the test names alone.

## 2. Backend test pyramid

| Level | Location | What it covers | Tools |
|---|---|---|---|
| Unit | `tests/unit/` | Domain (`Money`, EMI strategies, comfort, ranking), services with fake ports | pytest, hypothesis |
| Contract | `tests/contract/` | Every port is tested against **both** the Mock adapter and recorded real responses, so mock and real behave the same | pytest, recorded JSON fixtures |
| Integration | `tests/integration/` | Controllers with a real PostgreSQL (Docker), repositories, migrations, event bus | pytest, httpx test client, Testcontainers or Compose |

Naming: `test_<unit>_<scenario>_<expected>`, for example `test_calculate_reducing_balance_installment_rounds_last_installment_to_match_total`.

## 3. Properties and cases that must exist

**EMI engine (Layer 1), property-based with `hypothesis`:**
- Sum of all installments equals total payable, to the paise.
- Total payable is never below the principal for interest-bearing plans.
- A no-cost plan has extra-in-total of exactly zero.
- Installments are non-negative and the count equals the tenure.
- Result is deterministic: same inputs give the same output.
- Results match a hand-checked reference table (at least 10 rows, including the three design sample plans: ₹3,667 x 6, ₹3,850 x 6, ₹2,050 x 12 on ₹22,000).

**Gateway adapter (Layer 1):**
- Signature generation and verification (known-answer test).
- Timeout on a read call is retried; timeout on an initiate call is **not** retried and surfaces `PaymentGatewayTimeoutError`.
- Idempotency: same key returns the stored result.
- Webhook with a bad signature is rejected; a repeated valid webhook has no extra effect.
- Circuit breaker opens after the configured failures and closes after the cool-down.

**Comfort and ranking (Layer 3):** ratio maths, band boundaries (exactly 35% and 50%), "no plan fits", sorting stability, reason codes.

**Number audit (Layer 4):** every number in AI text is found in engine output; a single mismatched digit triggers fallback; numbers written in Tamil numerals or with different grouping are normalised before comparison.

**Privacy (Layers 2 and 3):** merchant endpoints never return income, EMIs, ratios or step history (test by asserting the exact response schema).

## 4. Frontend tests

| Level | Tools | What |
|---|---|---|
| Component | Vitest, Testing Library, axe | Every screen: renders each state (loading, empty, error, success), accessibility violations = failure |
| Hook | Vitest | Customer flow reducer transitions; money formatting (Indian grouping, paise to rupees) |
| End to end | Playwright | One happy path per app (merchant starts sale; customer completes flow in Tamil and in English) and the "AI unavailable" path |

Tests query by role and visible text, not by CSS classes or test IDs unless unavoidable.

## 5. Coverage thresholds (CI fails below these) `[Inferred targets]`

| Area | Threshold |
|---|---|
| `domain/` and number audit | 100% line and branch |
| `services/`, `adapters/` | 90% |
| Backend overall | 85% |
| Frontend overall | 80%; customer flow reducer 100% |

## 6. Fixtures and mocks

- Fixtures live next to the tests that use them (`tests/contract/fixtures/paytm/*.json`) and contain **no real merchant IDs, keys or customer data**.
- Mock adapters are real classes in `adapters/` (they are also the local-development default), not ad hoc patches inside tests.
- Time and randomness come from injectable `Clock` and `IdGenerator` classes so tests are deterministic.

## 7. What a reviewer checks

- New behaviour has a test that fails without the change.
- No test depends on test order, wall-clock time or the network.
- Edge cases from the layer's acceptance list are covered.
- Coverage did not drop.
