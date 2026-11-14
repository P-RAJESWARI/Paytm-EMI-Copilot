# design-patterns.md: Pattern catalogue

Use a pattern only where it solves a real problem in this codebase. Name it once in a class-level comment: `# Pattern: <Name>. <one line on why here>`. Do not stack patterns for show; a reviewer should be able to say what problem each one solves.

## 1. Where each pattern is used

| Pattern | Where | Problem it solves | Layer |
|---|---|---|---|
| **Port and Adapter** (hexagonal) | `PaymentGatewayPort` with `PaytmPaymentGatewayAdapter` and `MockPaymentGatewayAdapter`; later `SpeechPort`, `ExplanationTextPort` | Services depend on an interface, so the real vendor and a mock are interchangeable and tests need no network | 1, 4 |
| **Adapter** | Each vendor adapter | Translates vendor request and response shapes and errors into our domain types at the boundary | 1, 4 |
| **Factory** | `PaymentGatewayFactory`, `SpeechProviderFactory` | Chooses the Mock or real implementation from configuration in one place | 1, 4 |
| **Strategy** | `EmiCalculationStrategy` (reducing balance, no-cost, quoted total; ADR 0001), `PlanRankingStrategy`, `ComfortBandClassificationStrategy` | Rules that vary independently are swappable and unit-testable | 1, 3 |
| **Repository** | `SaleRepository`, `ConsentRecordRepository`, `PaymentAttemptRepository`, and so on | Keeps queries out of services and lets tests use fakes | 1, 2, 3 |
| **Value Object** | `Money` (paise via `Money.to_paise()`, ADR 0008), `PlanSnapshot`, `ComfortRatio` | Makes invalid states impossible and keeps rounding in one place | 1 |
| **DTO** | Everything in `dtos/` | Separates the public API contract from ORM models and domain types | all |
| **Observer** (event bus) | `DomainEventBus` with subscribers: audit logger, funnel event recorder, metrics, merchant status broadcaster | Reacts to "payment link created", "sale ready to pay" without coupling services together | 1, 2, 3 |
| **State** | `SaleStateMachine` (`CHOOSING`, `READY_TO_PAY`, `PAID`, `PAYMENT_NOT_COMPLETED`, `EXPIRED`) | Legal transitions are explicit and tested; no scattered status checks | 2 |
| **Decorator** | `AuditedExplanationService` wraps the AI explanation service | Adds number audit and template fallback without changing the AI adapter | 4 |
| **Template fallback (Null Object flavour)** | `TemplateExplanationService` | Always returns a safe explanation when AI is unavailable or fails the audit | 3, 4 |
| **Circuit Breaker and Retry** (resilience) | `core/resilient_http_client.py` | Stops one slow dependency from starving the rest | 1 |
| **Unit of Work** | Service-opened database transaction passed to repositories | One consistent write per use case, including append-only consent plus audit | 1 |
| **Container and Presentational components** (UI) | Frontend features | Separates data and flow logic from rendering | 2, 3 |
| **Finite state machine (UI)** | Customer flow reducer | The customer cannot reach "consent" without a confirmed budget and selected plan | 3 |

## 2. Layer-specific notes

### Layer 1 (gateway)
- The **port** is defined in the domain's terms (`discover_offers`, `create_payment_link`, `get_payment_status`, `verify_webhook`), never in Paytm's terms. Paytm field names stay inside the adapter.
- The **factory** returns the Mock unless `PAYMENT_GATEWAY_MODE=paytm`. With `paytm` and missing credentials, startup fails with a clear error instead of falling back (ADR 0004). Startup logs say which one is active.
- **Observer:** `PaymentLinkCreated` and `PaymentStatusChanged` events let audit and the merchant status feed subscribe without the gateway service knowing about them.

### Layer 4 (AI)
- LangGraph is used for the AI flows only (explain, audit, fallback, teach-back, weekly message), behind the same ports as any other implementation. The deterministic core must run and be tested without LangGraph installed.

## 3. Anti-patterns to avoid

- A `Manager`, `Helper`, `Utils` or `Handler` class that does several unrelated things.
- Abstract base classes with one implementation and no second one planned (use a plain class until a second implementation exists, except ports to external systems, which always get a Mock).
- Passing dictionaries between layers instead of typed objects.
- Business rules inside controllers, ORM models or React components.
- Global singletons holding mutable state.
