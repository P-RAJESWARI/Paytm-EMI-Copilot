# 0022: Layer 3 customer integration: single-use QR, consent scope, phone source, OTP attempts

Status: Accepted (owner, 2026-11-15, for decisions 1 to 3; the rest are orchestrator decisions in the plan the owner approved). Covers Layer 3 Phases 3B and 3C. Partly supersedes ADR 0021.

## Context
Layer 2 is merged (ADRs 0013 to 0019). The Phase 3A customer contract (ADR 0020, ADR 0021) now becomes a real, database-backed flow mounted in the main application, with a customer app. Several questions were left open by the Phase 3A handoff, and one of my own Phase 3A decisions disagrees with the rule files:
- ADR 0021 decision 3 lets a re-scan of the same QR open a new session. `security-and-compliance.md` section 4 and `api-conventions.md` section 6 say the QR token is single-use and a reused token answers 401.
- Layer 2's sale is fixed to one product at its full price (ADR 0014). Its chosen plan, the merchant screens M3 and M4, and the payment link all use that price.
- C9 shows "OTP sent to your phone ending 42", but no screen collects a phone number.
- C9 shows "2 tries left", but no rule says how many attempts an OTP has.

## Decision
1. **C6 alternatives (owner).** All three alternatives are shown with engine numbers.
   - Longer tenure is another offer on the same product at the same price, so the customer can choose it and consent to it.
   - Down payment and cheaper model show "Ask the shop to set this up". For the cheaper model, the merchant starts a new sale for the 64 GB phone.
   - Paying a down payment at the counter is a limit of this build and is stated as such.
   - Layer 2's sale and payment link do not change.
   - Consent carries the offer id and the figures shown, nothing else. The Phase 3A `productId` and `downPaymentInPaise` consent fields are removed. ADR 0021 decisions 1 and 2 are narrowed to this.
2. **Phone number source (owner: "get it from Paytm").**
   - A `CustomerContactPort` gives the customer's phone number as the payment side knows it. `MockPaytmCustomerContactAdapter` returns a synthetic number ending 42 and is announced in the startup logs (CLAUDE.md rule 10).
   - We know of no Paytm API that gives a merchant the customer's number before payment without the customer signing in with Paytm. The real adapter is therefore **[Verify with Paytm]** and not built.
   - Only the last two digits and a salted hash are stored. The plain number exists only in memory, to send the OTP (security-and-compliance.md section 2).
3. **OTP attempts (owner left the choice to the orchestrator).** These are demo values held in settings.
   - Each OTP allows 3 attempts, expires after 5 minutes, and can be resent after 30 seconds.
   - A wrong OTP answers 422 `OTP_INCORRECT` with an `attemptsRemaining` extension member on the problem body, as RFC 7807 allows.
   - After the third wrong attempt the OTP is spent and the answer is 422 `OTP_EXPIRED`; the screen offers to resend.
   - The wording stays calm, with no lockout language.
   - OTP request, OTP verification and consent are also rate limited per client.
4. **The QR exchange is single-use**, as the rule files say. This supersedes ADR 0021 decision 3.
   - Exchanging a QR sets `qr_token_exchanged_at` on the sale. Exchanging it again answers 401 `CUSTOMER_QR_TOKEN_INVALID` ("ask the shop for a new QR").
   - The merchant re-issues a QR with Layer 2's existing command, which only works while the sale is CHOOSING. A new QR therefore never reaches a sale that already has consent evidence.
   - Exchanging a new QR revokes the sale's earlier customer session.
   - The customer session token is random and stored only as a hash. It lasts 30 minutes and lives only in memory on the phone, so reloading the page means asking the shop for a new QR.
5. **Plan names** follow Layer 2's merchant UI: "No-cost EMI" or "EMI" from `emiType`, plus the lender line. There is no `planKind` field.
6. **One API, one client.** The customer routers are mounted in `main.py`. `backend/openapi.json` and the generated api-client cover both apps. The Phase 3A contract application, `openapi.customer.json` and `make openapi-customer` are removed (ADR 0020 decision 7 is complete).
7. **Voice is Layer 4.** The C2 microphone, C7 audio and C8 teach-back are not built in Layer 3. C7 shows the text from `TemplateExplanationService`, the template fallback that Layer 4's audited AI explanation will wrap.
8. **Consent and the sale move together.** One unit of work appends the hash-chained consent record and agrees the plan on the sale (CHOOSING to READY_TO_PAY). Layer 2's `MarkSaleReadyToPayService` and customer consent share one in-transaction step. The merchant's live status feed receives READY_TO_PAY through the existing broadcaster, and Layer 2's `MockCustomerSimulator` remains a labelled demo stand-in.
9. **Funnel stages from the customer flow.** BUDGET_TOLD (carrying the budget) and PLANS_VIEWED are recorded once per sale, through domain events and Layer 2's `FunnelEventRecorder` (Observer).

## Consequences
- A customer who wants the cheaper model or a down payment needs the merchant's help, and the design's C6 "choose" for those two becomes "ask the shop". The design's happy path (consent to plan A at full price) is unaffected.
- Real phone delivery and the real contact source wait on Paytm. The demo uses a fixed mock OTP, documented in the handoff and never logged.
- A reloaded customer page needs a new QR from the shop. This is the price of keeping the token out of browser storage.
