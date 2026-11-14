# backend.md: Backend coding rules

Applies to everything under `backend/`. Stack: Python 3.12 (decided), FastAPI, Pydantic v2, SQLAlchemy 2.0 (sync), Alembic, httpx (library choices are defaults).

## 1. Folder layout

```
backend/
  pyproject.toml  uv.lock  alembic.ini
  alembic/versions/
  src/emi_copilot/
    main.py                     application factory only; no business logic
    config/settings.py          typed settings from environment (pydantic-settings)
    api/
      controllers/              HTTP layer: routing, validation, status codes (one file per resource)
      dependencies.py           dependency-injection wiring
      error_handlers.py         maps domain errors to problem+json responses
    services/                   use-case orchestration; one class per use case or cohesive group
    repositories/               database access only; one class per aggregate
    models/                     SQLAlchemy ORM entities (tables)
    dtos/                       Pydantic request and response schemas (the API contract)
    domain/                     pure business logic, no I/O, no framework imports
      money.py                  Money value object (Decimal, paise)
      emi/                      EMI calculation strategies
      comfort/                  comfort ratio and band classification (Layer 3)
      ranking/                  plan ranking and reason codes (Layer 3)
      errors.py                 typed domain errors
      events.py                 domain event classes
    adapters/                   everything that talks to the outside world
      payment_gateway/          port.py, paytm_adapter.py, mock_adapter.py, factory.py, checksum.py
      ai/                       Layer 4: speech, text, number audit, LangGraph flows
    events/                     event bus and subscribers (Observer)
    core/                       logging, resilient HTTP client, clock, id generation
  tests/
    unit/  integration/  contract/
```

## 2. Layering rules (enforced by the reviewer agent)

| Layer | May import | Must not |
|---|---|---|
| `controllers` | `services`, `dtos`, `domain.errors` | Touch repositories, adapters, ORM models, or contain business logic |
| `services` | `repositories`, `adapters` (ports only), `domain`, `events` | Import FastAPI or return HTTP concepts |
| `repositories` | `models`, `domain` types | Contain business rules; return ORM models to controllers |
| `adapters` | `domain`, `core` | Import services or repositories |
| `domain` | standard library only | Import anything else in the app, the database, HTTP or the clock directly |

Services depend on **ports (abstract interfaces)**, never on concrete adapters. Concrete adapters are chosen in `dependencies.py` through a factory.

## 3. Naming

- Modules and functions: `snake_case`, fully spelled: `calculate_monthly_installment_amount`, `find_open_sales_for_merchant`.
- Classes: `PascalCase` with the role in the name: `PaytmPaymentGatewayAdapter`, `SaleRepository`, `StartSaleService`.
- Booleans read as questions: `is_cooling_off_period_active`, `has_customer_given_comfort_check_consent`.
- Money variables carry the unit: `price_in_paise`, never `price` or `amt`.
- Test names: `test_<unit>_<scenario>_<expected>`.
- No single-letter names except loop indices in comprehensions.

## 4. Documentation per function

Every function and method has a one or two line docstring stating its purpose. Do not restate the signature.

```python
def retry_with_exponential_backoff(...):
    """Retries an idempotent call with growing delays and gives up after the configured attempts."""
```

Classes that apply a pattern state it: `# Pattern: Strategy. Interchangeable EMI calculation rules.`

## 5. Money and numbers

- Domain code uses `Decimal`. Parse from strings, never from floats.
- Round once, at the end, half-up to paise. The last installment absorbs any rounding remainder; document this in `EmiCalculationStrategy`.
- Persist and transmit integer paise (`BigInteger` column, `amountInPaise` on the wire).
- Format for display only in the frontend, using Indian digit grouping.

## 6. Error handling

- Domain and service code raise **typed errors** from `domain/errors.py` (for example `OfferNotFoundError`, `PaymentGatewayTimeoutError`, `ConsentAlreadyGivenError`). Never raise bare `Exception` or return error strings.
- `error_handlers.py` converts them to RFC 7807 `application/problem+json` (see `api-conventions.md`).
- Adapters translate vendor failures into domain errors at the boundary. Raw vendor payloads never leave an adapter.
- Never log or return stack traces, secrets, tokens or personal data in error bodies.
- Retry **only idempotent** calls (reads, status checks). Never retry "initiate" or "create" calls without an idempotency key.

## 7. External calls (adapters)

- Use the shared resilient client in `core/`: explicit connect and read timeouts, bounded retries with jitter, and a circuit breaker.
- One timeout setting per dependency (gateway, speech, LLM) in settings.
- Every adapter has a **Mock** sibling that implements the same port and is the default in tests and local development.
- Adapters have contract tests that run against both the Mock and recorded real responses.

## 8. Database

- Alembic migrations only; never alter schema by hand. One migration per logical change, reversible when possible.
- Repositories own queries. Services never build SQL.
- Transactions are opened by the service (unit of work) and passed to repositories.
- Tables: singular snake_case names; every table has `id`, `created_at`, `updated_at`. Append-only tables (`consent_record`, `audit_event`) have no `updated_at` and no update or delete methods.
- Index every foreign key and every column used in a `WHERE` by the dashboard queries.

## 9. Configuration and secrets

- Settings come from environment variables through a typed settings class. `.env.example` lists every variable with a safe placeholder. Real `.env` is git-ignored.
- No secret, key, token or merchant ID in code, tests, fixtures or logs.

## 10. Logging

- Structured JSON logs with a correlation ID on every line.
- Redact phone numbers (keep last two digits), tokens and anything under `security-and-compliance.md` "never log".
- Log events, not payloads.

## 11. Quality gates (`make check` must pass)

`ruff check`, `ruff format --check`, `mypy --strict`, `pytest` with coverage thresholds from `testing.md`. A failing gate blocks the commit.
