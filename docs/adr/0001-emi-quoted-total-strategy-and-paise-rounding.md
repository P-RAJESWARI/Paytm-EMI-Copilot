# 0001: EMI quoted-total strategy and paise rounding

Status: Accepted (owner, 2026-11-14). Answers Layer 1 questions 1, 2 and 3.

## Context
No annual rate makes a reducing-balance schedule come out at exactly ₹3,850 × 6 or ₹2,050 × 12 on ₹22,000. For example, 16.9449% gives 5 × ₹3,850.00 + ₹3,850.02. The design figures match exactly only when the lender quotes the extra cost: (22,000 + 1,100) / 6 and (22,000 + 2,600) / 12. Paytm's Tenures API returns `emi` and `interest` per plan, so lenders really do quote this way. Separately, 6 × ₹3,667 = ₹22,002, which is not the ₹22,000 total of no-cost plan A.

## Decision
- Add a `QuotedTotalStrategy`: principal plus the quoted extra, split evenly, with the last installment absorbing the remainder. Design plans B and C use it, and so does every offer that comes from the gateway.
- `ReducingBalanceStrategy` remains for rate-quoted offers and as a cross-check.
- `NoCostStrategy` splits the principal evenly and leaves the extra at exactly zero.
- The engine rounds half-up **to the paise**. The API exposes `monthlyInstallmentInPaise` (the regular installment) and `lastInstallmentInPaise`. Plan A is 366667 and then 366665.
- The frontend shows rupees rounded half-up (₹3,667). The Layer 4 number audit compares against the displayed rupee values.
- Restated acceptance criterion: "Plan A displays ₹3,667 × 6 and its installments sum to exactly ₹22,000.00. Plans B and C are exactly ₹3,850.00 × 6 and ₹2,050.00 × 12."
- If the gateway's quoted EMI differs from our engine by more than ₹1 per installment, show the gateway (lender) figure and write an `OFFER_QUOTE_MISMATCH` audit event. Never hide the offer.

## Consequences
Every number the customer sees is either the lender's quote or derived from it exactly. The schedule always sums to the total to the paise.
