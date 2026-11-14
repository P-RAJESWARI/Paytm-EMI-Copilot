# 0010: Paytm link fields, subvention extra cost and create-call outcomes

Status: Accepted, 2026-11-14. Items 1 and 2 were answered by the owner; item 3 is an orchestrator decision that applies ADR 0005. All Paytm items are **[Verify]**.

## 1. Create Link optional-or-mandatory fields (owner)
The docs table marks `partialPayment` (the only listed value is "true") and `bindLinkIdMobile` as mandatory, but the official minimal sample leaves both out. **Decision: omit both**, matching the sample. This also avoids enabling partial payment on an EMI order and avoids sending a phone number.

## 2. "Extra in total" for SUBVENTION plans (owner)
The Tenures API returns `interest` and, for subvention plans, `gratifications` {`value`, `type` DISCOUNT|CASHBACK}.

**Decision:**
- `quoted_extra_in_total = interest − gratification value`, for both DISCOUNT and CASHBACK, and never below zero.
- The emi type is `NO_COST` only when that net extra is zero; otherwise it is `STANDARD`.
- `quoted_monthly_installment` stays Paytm's `emi`.
- If `emi` and the net extra disagree by more than ₹1 per installment, ADR 0001's `OFFER_QUOTE_MISMATCH` audit applies.

Consequence: a cashback plan can show as no-cost although the customer pays the interest up front and receives the cashback later. Layer 3 wording should make the cashback timing clear.

## 3. Create-link failures with an unknown outcome (orchestrator, applies ADR 0005)
- If a create-link call fails after the request may have reached Paytm, the adapter raises `PaymentGatewayTimeoutError` (outcome unknown) and the attempt is stored as `OUTCOME_UNKNOWN`. Such failures are read or write timeouts, connections dropped after sending, and **any 5xx response**.
- Failures where the request provably never left (connect error, connect or pool timeout, circuit open) raise `PaymentGatewayUnavailableError`. Such an attempt is stored as `LINK_CREATION_FAILED`.
- Nothing is ever re-sent automatically.
