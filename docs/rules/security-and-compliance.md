# security-and-compliance.md: Security, privacy and compliance rules

These rules apply to every layer. A violation blocks the merge request.

> Items marked **[Verify]** depend on facts to confirm with Paytm, the lender or compliance before any real pilot. This document is engineering guidance, not legal advice.

## 1. Card and payment data

- **Never** receive, log, store, cache or pass through card number, expiry or CVV. No form field for them exists in this product.
- Payment and card entry happen on Paytm (payment link, checkout or the EDC). We handle only order IDs, amounts, statuses and Paytm-issued references.
- Do not persist the card BIN or any card detail beyond what Paytm's APIs return for display **[Verify with Paytm whether even transient BIN handling is allowed in our flow]**.
- Confirm payment status **server-side** with a Paytm status call or a verified webhook. Never trust a client-side "success".

## 2. Personal and financial data

| Data | Rule |
|---|---|
| Phone number | Store only a salted hash for velocity checks plus the last two digits for display. The OTP flow uses the plain number only in memory |
| Comfort-check inputs (income, existing EMIs) | Synthetic on the hackathon build. In production store derived numbers and a consent reference only, never raw statements **[Verify]** |
| Voice audio | **Never stored.** Stream to speech-to-text and discard |
| Consent records | Append-only, hash-chained, store the frozen plan snapshot shown |
| AI prompts and traces | Contain no names, phone numbers or account data; redact before tracing |

## 3. Never log

Tokens (merchant, customer session, QR), OTPs, full phone numbers, signatures and secrets, request bodies containing personal data, card-related fields (should never exist), and raw vendor responses.

## 4. Authentication and sessions

- Merchant: device pairing by PIN issues a short-lived bearer token; PIN attempts are rate limited and lock after repeated failures.
- Customer: QR carries a signed, expiring, single-use token exchanged for a session token bound to **one sale**. Expired or reused tokens return 401 with a calm "ask the shop for a new QR" code.
- Authorisation: a merchant can only access their own sales and reports (enforced in the service layer and tested).
- Rate limits on token exchange, OTP request, OTP verify and consent endpoints.

## 5. Secrets and dependencies

- Secrets only via environment or a secret manager. `.env` is git-ignored; `.env.example` has placeholders. A secret scanner runs in pre-commit and CI.
- Pin exact dependency versions. Prefer versions at least two weeks old; skip freshly published releases. Run a vulnerability scan in CI.
- TLS 1.2+ for all external calls. Verify certificates; never disable verification, even in tests.

## 6. Comfort check: wording and behaviour

- Exactly three bands: **Comfortable, Stretching, Risky**, each with an icon and a word.
- Never "approved", "declined", "eligible for credit" or "rejected". The lender, not this product, decides credit.
- Consent first, in plain language, with a statement that the shop cannot see the information.
- Thresholds in code are demo heuristics (below 35% Comfortable, 35 to 50% Stretching, above 50% Risky) held in one configuration class, labelled as heuristics, and **[Verify]** with a lender or risk team before any pilot.

## 7. Lending and consumer-protection behaviours the product must show

Based on RBI Digital Lending Directions, 2025 as summarised in earlier project research **[Verify exact obligations and who they bind with Paytm and the lender]**:

- Show every eligible offer; never hide a plan. If no plan fits the budget, still show them, labelled "above your budget".
- Show lender or funder, amount, tenure and total extra you pay on each plan; show a plain-language key-facts summary before consent.
- Explain the cooling-off right at consent and on the receipt. The wording is a **placeholder** until the lender confirms the period.
- No automatic upgrades or limit changes without explicit consent.

## 8. AI guardrails (Layer 4)

| AI may | AI may not |
|---|---|
| Turn speech into a budget number (the customer confirms it on screen) | Approve or decline credit |
| Explain plans from structured data | Calculate EMI, totals, ratios or bands |
| Check whether the customer understood the key terms (advisory only) | Hide an eligible option or call a plan "best for you" |
| Write a short merchant weekly message from aggregates | Trigger payment, OTP or consent |
| | Receive personal data, call any tool or write to the database |

Number audit is mandatory. Prompt-injection stance: product names, offer text and customer speech are untrusted data, never instructions.

## 9. Audit and evidence

- Append-only `audit_event` and `consent_record` tables; no update or delete code paths exist.
- Each consent row stores a hash of the previous row so tampering is detectable.
- Audit events record: AI fallback used, audit mismatch, handoff created, status changed, webhook rejected.

## 10. Honest limits (state in every demo and README)

Lender decisions, account data and settlement data are mocked or synthetic in the hackathon build. The comfort check is not a credit decision.
