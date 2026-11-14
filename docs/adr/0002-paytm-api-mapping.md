# 0002: Paytm API mapping for the payment gateway port

Status: Accepted (owner, 2026-11-14). Answers Layer 1 questions 4, 5, 6 and 8. Every item here is **[Verify]**: it was checked on paytmpayments.com/docs on 2026-11-14 through a content extraction of JS-heavy pages, not against a live account.

## Decision
| Port method | Paytm API | Staging URL |
|---|---|---|
| `discover_offers` | Banks API, then Tenures API for each bank and card type (EMI Subvention). No card fields are sent | `POST https://securestage.paytmpayments.com/theia/api/v1/emiSubvention/banks?mid=` and `.../tenures?mid=` |
| `create_payment_link` | Create Link API with `simplifiedSubvention` (item-based, `selectPlanOnCashierPage: true`) | `POST https://securestage.paytmpayments.com/link/create` |
| `get_payment_status` | Transaction Status API v3 | `POST https://securegw-stage.paytmpayments.in/v3/order/status` |
| `verify_webhook` | Link Payment Status webhook: key/value pairs with a `CHECKSUMHASH` field | our `statusCallbackUrl` |

- Settings hold one base URL per API family. Defaults are the staging hosts above. Production hosts are not on the docs pages, so production has **no default** and must be set explicitly.
- We send our `order_id` as `linkOrderId` and use the same value for the v3 status call **[Verify]**.
- The webhook is accepted as an `application/x-www-form-urlencoded` POST **[Verify]**. `CHECKSUMHASH` is verified over the parsed key/values before any field is used. A mismatch returns 401 and writes an audit event.
- The Validate API needs a card BIN or number, so it is **never used** (no-card-data rule). The customer picks the plan on Paytm's page.
- Paytm amounts are rupees (decimal) and are converted to paise at the adapter boundary through `Money`.
- Cardless credit (design plan C) is not covered by Banks and Tenures. The Paytm adapter returns card EMI offers only. The Mock includes plan C, labelled as a mock.
- Mock lender labels are "Brand" (A), "Your card's bank" (B) and "Demo cardless lender (Mock)" (C). No real bank names.
- All Paytm URLs, field names and result codes live in `adapters/payment_gateway/paytm_api_definitions.py`.
