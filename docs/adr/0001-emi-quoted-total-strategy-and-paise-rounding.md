# 0001: EMI quoted-total strategy and paise rounding

Status: Accepted (owner, 2026-11-14). Answers Layer 1 questions 1, 2 and 3.

## Context
The design quotes plans B and C by their extra cost (₹1,100 over 6 months and ₹2,600 over 12 months on ₹22,000), not by a rate. Paytm's Tenures API also returns `emi` and `interest` for each plan. Separately, 6 × ₹3,667 = ₹22,002, which is not the ₹22,000 total of no-cost plan A.

Correction (2026-11-14, found while implementing step 1.2): an earlier draft said no annual rate gives exactly ₹3,850 × 6. That was wrong. With exact maths and one half-up rounding, 16.9449% gives 6 × ₹3,850.00 (exact EMI ₹3,850.000211…), and 21.14175% gives 12 × ₹2,050.00. Those rates are artefacts reverse-engineered from the quoted amounts, not rates a lender publishes, so the decision below stands.

## Decision
- Add a `QuotedTotalStrategy`: principal plus the quoted extra, split evenly, with the last installment absorbing the remainder. Design plans B and C use it, and so does every offer that comes from the gateway.
- `ReducingBalanceStrategy` remains for rate-quoted offers and as a cross-check. It computes with `fractions.Fraction` (standard library, exact), because a monthly rate of annual/1200 has no finite decimal form and a 34-digit Decimal misrounds exact half-paisa cases. The result becomes `Money` once and is rounded only by `Money.rounded_to_paise()`.
- `NoCostStrategy` splits the principal evenly and leaves the extra at exactly zero.
- The engine rounds half-up **to the paise**. The API exposes `monthlyInstallmentInPaise` (the regular installment) and `lastInstallmentInPaise`. Plan A is 366667 and then 366665.
- The frontend shows rupees rounded half-up (₹3,667). The Layer 4 number audit compares against the displayed rupee values.
- Restated acceptance criterion: "Plan A displays ₹3,667 × 6 and its installments sum to exactly ₹22,000.00. Plans B and C are exactly ₹3,850.00 × 6 and ₹2,050.00 × 12."
- If the gateway's quoted EMI differs from our engine by more than ₹1 per installment, show the gateway (lender) figure and write an `OFFER_QUOTE_MISMATCH` audit event. Never hide the offer.

## Consequences
Every number the customer sees is either the lender's quote or derived from it exactly. The schedule always sums to the total to the paise.
