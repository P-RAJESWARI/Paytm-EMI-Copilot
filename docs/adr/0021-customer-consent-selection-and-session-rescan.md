# 0021: Customer consent names the exact selection; a re-scan keeps evidence

Status: Partly superseded by ADR 0022 (decisions 1 to 3: consent covers same-product plans only, and the QR exchange is single-use). Decisions 4 to 6 stand. Follows the Phase 3A review of the customer contract (ADR 0012, ADR 0020).

## Context
The first Phase 3A contract had several gaps:
- Consent carried only an offer id. A customer who chose "₹4,000 down" or the cheaper 64 GB model on C6 got a snapshot of the ₹22,000 128 GB plan at ₹3,667 a month.
- The plan was re-quoted at consent time with no check against what C9 had shown.
- Re-scanning the QR wiped the session, including consent records.
- An unknown session id and a wrong token gave different answers, so session ids could be probed.
- The idempotency fingerprint hashed the 6-digit one-time code, which is effectively the code itself.

CLAUDE.md section 2 rule 8 says consent records are evidence and store the exact plan shown.

## Decision
1. **Consent names the exact selection and the shown figures.** The selection is the offer id, the product (the session's item, or a cheaper model offered on C6) and the down payment (0, or exactly the DownPaymentRule suggestion for that plan). The shown figures are the monthly installment and the total payable from C9. The server re-quotes that selection.
   - A product or down payment the session does not offer is 422 `INVALID_PLAN_SELECTION`.
   - An offer that is not quoted is 404 `OFFER_NOT_FOUND`.
   - If the shown monthly or total differs from the re-quote, the answer is 409 `SHOWN_PLAN_CHANGED` and nothing is recorded.
   - The stored snapshot holds the plan's schedule plus productId, productName, price, down payment and financed amount. The receipt shows the same.
2. **The merchant side of a changed selection is an open question for Phase 3C.** Consenting to a cheaper model or a down payment changes what the merchant's sale must collect: another product, or the price less a down payment paid at the counter. Layer 2 owns the sale, so how the merchant sees this and collects the down payment is decided in Phase 3C with Layer 2.
3. **A re-scan keeps evidence.** Scanning the same QR again issues a new session token with a fresh lifetime, and the previous token stops working. The budget, the comfort-check choice, the one-time code state and every consent record are kept. A consent replay with the old Idempotency-Key returns the original consent id.
4. **Session probing gets one answer.**
   - A missing token, or a token that opens no session, is 401 `CUSTOMER_SESSION_TOKEN_INVALID`.
   - A valid token used with any other session id is 404 `CUSTOMER_SESSION_NOT_FOUND`, with the same body whether that id exists or not.
5. **The one-time code is kept out of the idempotency fingerprint.** The fingerprint covers the selection and the shown figures only. The same key and selection with a different code is the same request and replays the stored result.
6. **POST /customer-sessions sets Location** to `GET /customer-sessions/{customerSessionId}`. That endpoint returns the session summary and the customer's own progress, never the token.

## Consequences
- The frontend must send the selection and the figures it displayed. It re-shows the plans on 409 `SHOWN_PLAN_CHANGED`.
- Phase 3C carry-overs:
  - Rate limits on one-time code verification and on consent, plus a limit on wrong-code attempts (api-conventions.md section 6).
  - Fold the wiring in `api/customer_contract_application.py` into `api/dependencies.py` when the routers are mounted in `main.py`.
  - `previousMonthlyInstallmentInPaise` on alternatives is the lender's quoted figure, while `isLowerMonthlyAmount` compares the largest single installments (ADR 0020 decision 3). The two agree on the design data. The divergence is documented and is revisited if a quote ever differs from the schedule.
  - The merchant-side effect of a changed selection (decision 2).
