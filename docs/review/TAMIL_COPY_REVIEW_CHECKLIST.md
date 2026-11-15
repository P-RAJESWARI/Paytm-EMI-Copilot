# Tamil copy review checklist

Every Tamil string in this build is a draft until a native Tamil speaker reviews it (open question Q13). Each draft line ends with `// draft: needs native review` in the frontend, or `# draft: needs native review` in the backend. Remove the marker only after review.

## Where the drafts are

| Area | File |
|---|---|
| Customer screens C1 to C10 | `frontend/apps/customer-web/src/i18n/*Translations.ts` |
| Merchant screens M1 to M8 | `frontend/apps/merchant-web/src/i18n/*Translations.ts` |
| Shared labels (bands, money) | `frontend/packages/shared-i18n/src/sharedTranslations.ts` |
| Template explanation (C7 fallback) | `backend/src/emi_copilot/services/customer/template_explanation_service.py` |
| Teach-back feedback (C8) | `backend/src/emi_copilot/services/ai/teach_back_feedback.py` |
| Weekly message template (M5/M8) | `backend/src/emi_copilot/domain/reports/weekly_message_template.py` |
| Tamil number words (audit and voice) | `backend/src/emi_copilot/domain/number_audit/number_words.py` |
| Tamil forbidden phrases (audit) | `backend/src/emi_copilot/domain/number_audit/forbidden_wording_guard.py` |
| Mock AI text (demo) | `backend/src/emi_copilot/adapters/ai/mock_explanation_text_adapter.py` |

## What the reviewer checks
- [ ] **Plain spoken Tamil** that a shop customer would use, not formal or literary Tamil. Common English loan words (EMI, OTP, QR) stay in English.
- [ ] **"Extra you pay"** is never translated as interest (வட்டி). The product never shows an interest rate.
- [ ] **Band words** (Comfortable, Stretching, Risky) read as advice, never as approved or declined, and never as a credit decision.
- [ ] **No urgency** and no "best for you" or "recommended" meaning, even softened.
- [ ] **Money reads correctly** with ₹ and Indian digit grouping (₹1,84,000). Numbers are written in digits, never in words.
- [ ] **The number words 1 to 12** in `number_words.py` are the words people actually say for tenures, for example ஆறு (6) and பன்னிரண்டு (12).
- [ ] **The forbidden phrases** in `forbidden_wording_guard.py` cover the usual Tamil ways of saying "approved", "rejected", "interest rate" and "best plan".
- [ ] **Cooling-off wording** stays clearly a placeholder until the lender gives the period.
- [ ] **Text-to-speech** (`bulbul:v3`, Tamil voice [Verify]) reads ₹ amounts and "EMI" naturally. Listen to C7 in Tamil with real Sarvam mode.

## Sign-off
| Reviewer | Date | Files reviewed | Notes |
|---|---|---|---|
| | | | |
