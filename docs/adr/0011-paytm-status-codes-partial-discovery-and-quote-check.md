# 0011: Paytm status codes, link error codes, partial discovery and the quote check

Status: Accepted by the owner at checkpoint 2, 2026-11-14. All Paytm items are **[Verify]**.

## Decisions
1. **v3 status codes 334, 335 and 501 are not payment failures.** The docs list them under TXN_FAILURE, but none of them means the payment failed.
   - 501 (Paytm server down) becomes `PaymentGatewayUnavailableError`, and the status check can be repeated later.
   - 334 (invalid order id) and 335 (invalid MID) become `PaymentGatewayRequestRejectedError`, because they point to our configuration or our order id.
   - Only the remaining TXN_FAILURE codes map a payment to FAILED.
2. **Create Link body result codes 501 and 502 count as rejected, not outcome unknown.** The owner chose this over the outcome-unknown recommendation.
   - The adapter raises `PaymentGatewayRequestRejectedError`, and the attempt is stored as `LINK_CREATION_FAILED`.
   - Accepted risk: if Paytm did make a link, a retry with a new key could make a second one.
   - HTTP-level 5xx responses and timeouts are unchanged: they remain outcome unknown under ADR 0010 §3.
3. **Partial offer discovery fails the whole call.** If any Banks or Tenures call is refused, `discover_offers` raises a typed error and returns no offers. We never silently hide an eligible plan (security-and-compliance.md §7).
4. **The ₹1 quote-versus-schedule check lives in the service, not the contract test.**
   - The shared contract test checks structure only: positive figures, a valid tenure and unique offer ids.
   - `OfferDiscoveryService` runs the cross-check and writes `OFFER_QUOTE_MISMATCH` without hiding the offer (ADR 0001).
   - This keeps real cashback plans (ADR 0010 §2) valid.

## Orchestrator follow-ups in step 1.8 (no owner decision needed)
- `config/settings.py` must not import adapter code. Staging URL defaults are applied by the factory from `paytm_api_definitions.py`.
- The `port.py` docstrings are updated to match ADR 0010 §3 and this ADR.
- An unreadable create-link reply (HTTP 2xx but unparseable) is stored as `OUTCOME_UNKNOWN`, because Paytm may have made the link. It is never re-sent.
