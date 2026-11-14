# 0014: Sale state machine, chosen plan and payment links per sale

Status: Accepted (owner, 2026-11-14: Layer 2 plan Q2, Q5, Q6, Q8, Q17, Q18).

## Decision
- **Statuses the merchant can see (owner, Q2):** CHOOSING, READY_TO_PAY, PAID, PAYMENT_NOT_COMPLETED, EXPIRED. No "scanned" or other step signal (CLAUDE.md rule 6 updated).
- **`SaleStateMachine` (Pattern: State), table-driven:** CHOOSING → READY_TO_PAY (customer agreed; needs a `ChosenPlan`), CHOOSING → EXPIRED, PAYMENT_NOT_COMPLETED → READY_TO_PAY (merchant retries). Anything else is 409 `SALE_STATE_CONFLICT`. Gateway reports go through a tolerant `apply_payment_outcome`: PAID is final, a late PAID after PAYMENT_NOT_COMPLETED is accepted, and reports on CHOOSING/EXPIRED are ignored and audited.
- **Expiry:** a sale still CHOOSING 60 minutes after it started is EXPIRED, dated at the deadline, applied deterministically inside the unit of work of each sale read or command.
- **`ChosenPlan` (Value Object):** frozen figures exactly as shown: the lender's quoted monthly (ADR 0001), extra in total and total payable, plus offer id, plan kind, lender label and tenure. New DTOs use `monthlyInstallmentInPaise`.
- **Payment:** one sale has many payment attempts (`payment_attempt.sale_id`). A link is created only for READY_TO_PAY (or after PAYMENT_NOT_COMPLETED, which first retries). The re-quoted offer must equal the `ChosenPlan` or the call is 409 `CHOSEN_PLAN_NO_LONGER_OFFERED`. A new link is refused with 409 `PAYMENT_LINK_ALREADY_ACTIVE` while the latest attempt may still be paid, so one sale never has two payable links.
- **EDC path:** instructions only. PAID comes only from a verified webhook or a server-side status check; there is no "mark paid" action (security §1).
- **Payment link without a customer phone:** shown on the tablet as a QR and copy button; nothing is sent.
- **Stale creation:** an attempt LINK_CREATION_IN_PROGRESS for 2 × (connect + read timeout) is recorded as OUTCOME_UNKNOWN on replay and never re-sent (closes Layer 1 handoff question 2).

- **A sale is never stuck without a link (gate review B1, `LatestSaleAttemptCheck`):** on a new key, a latest attempt still LINK_CREATION_IN_PROGRESS past the stale limit is recorded as OUTCOME_UNKNOWN, whatever the key. An OUTCOME_UNKNOWN attempt older than the stale limit (measured from `created_at`) gets one server-side status check; if the gateway answers NOT_FOUND, a new link is allowed. The old attempt row is not changed and stays as evidence; PENDING or PAID answers apply as usual and keep the refusal. The proof counts only if, under the sale row lock, that attempt is still the latest, still OUTCOME_UNKNOWN and still has no link URL (a late create outcome may have filled one in).
- **Reports on a replaced attempt:** a PAID report always applies to the sale (money was taken); any other outcome applies only when it comes from the sale's latest attempt, so a late failure on a replaced attempt cannot undo a live new link. The ignored report is audited as `SalePaymentOutcomeIgnored` with reason `ATTEMPT_REPLACED` (the other reason is `SALE_NOT_AWAITING_PAYMENT`).
- **Bare Layer 1 `POST /payment-links`** (no sale, no customer agreement) is `deprecated` in OpenAPI and no longer sends `Location` (its status URL always answered 404 for sale-less attempts). The merchant app does not use it. Retiring it is an owner decision.

## Consequences
- While the gateway is down, the B1 status check makes `POST /sales/{id}/payment-links` answer 502/504.
- The stale limit (2 × (connect + read) = 26 s) has no margin over the HTTP client's worst case, and Paytm might still finish a link after we gave up; add an overall deadline or a margin before paytm mode.
- The under-lock check reads the latest attempt without locking its row, so a webhook for that attempt arriving at the same moment is not seen. This only matters if the gateway answered NOT_FOUND and then reports on the same order. Locking the attempt row too would risk deadlocks; accepted.
- Payment-attempt idempotency keys are still unique across all shops: a cross-shop collision answers 422; on the deprecated bare endpoint the same key and body would replay another shop's link. Scoping keys per merchant is open.
