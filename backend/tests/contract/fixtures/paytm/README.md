# Paytm fixtures: documented-shape fixtures [Verify]

These files are **documented-shape fixtures [Verify]** (ADR 0007). They were written by hand
from the public paytmpayments.com/docs pages (checked 2026-11-14 through a content extraction,
not against a live account). They are **not** recorded Paytm responses. Replace them with
recordings once staging keys exist.

Every value is synthetic:

- Merchant id `SYNTHETICMID00000001`; the tests sign with the synthetic key `0123456789abcdef`.
  Neither is a real credential.
- Bank `Demo Bank A` / `DEMOA`; no real bank name.
- Order, transaction, plan and link ids start with `ORDER-SAMPLE-`, `SYNTHETIC-` or `9000000`.
- URLs are under `example.test`, which never resolves.
- The webhook's `PAYMENTEMAILID` and `PAYMENTMOBILENUMBER` are synthetic. They exist only to
  prove the adapter never reads, logs or returns them.
- Card-like fields in `status_txn_success.json` (`cardScheme`, `lastFourDigit`, `authCode`,
  `rrnCode`) hold placeholders. They exist only to prove the mapper drops them.

No signature is stored here. The tests sign status replies and webhook fields at run time.

## Shape choices that are [Verify]

- Every JSON reply is the `{"head": ..., "body": ...}` envelope, and the documented "response
  body" fields sit inside `body`.
- Banks: each `emiTypes` entry holds a `cardTypes` array and one `bankDetails` object. This is
  the most literal reading; the docs do not confirm the nesting.
- Tenures: `gratifications` is one `{value, type, label}` object, as the docs table shows.
  `itemBreakUp` is left out because its shape is not documented.
- Amounts mix JSON numbers and text (`"2050.00"`), as the docs pages do. The adapter accepts both.
- Banks and Tenures result codes are not documented. These fixtures use the placeholders
  `SYNTHETIC-SUCCESS-CODE` and `SYNTHETIC-FAILURE-CODE`. The adapter reads only `resultStatus`
  (`S` or `F`).
- Create Link: `status`, `expiryDate` and `createdDate` are left out because their value formats
  are not documented. The adapter does not read them.
- Status `txnType`, `paymentMode` and `txnDate` are placeholders because their values are not
  documented.
- The 12-month cashback plan uses a small ₹10 cashback. A real cashback plan's `emi` (gross
  interest) may differ from the schedule built from the net extra by more than ₹1. That is a
  valid gateway answer: the contract suite checks offers for structure only, and the ₹1 check
  with its `OFFER_QUOTE_MISMATCH` audit lives in `OfferDiscoveryService` (ADR 0011 decision 4).
  A unit test covers such a plan.
- Error replies are derived from these files in the tests by changing `resultCode` only: v3
  status 501, 334 and 335 (ADR 0011 decision 1) and Create Link 501 and 502 (decision 2).
