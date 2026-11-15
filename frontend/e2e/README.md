# Merchant and customer end-to-end tests (Playwright)

The Layer 2 and Layer 3 happy paths of testing.md section 4, run in a real Chromium against the
real backend, merchant-web and customer-web. They also run axe on every merchant and customer
screen, including colour contrast, which the jsdom component tests cannot measure. It is slow and needs a browser, so it is **not** part
of `make check`.

## How to run

```sh
make frontend-setup   # once: the locked frontend dependencies
make e2e-setup        # once: downloads Playwright's Chromium (the only network use)
make e2e              # every run
```

`make e2e`:

1. starts the Compose PostgreSQL if needed (`make db-up`);
2. drops and recreates the `emi_copilot_e2e` database in it, then migrates and seeds it with the
   demo shop RAVI-0193 and its synthetic week (`backend/scripts/seed_demo_data.py`);
3. runs Playwright, which starts the backend, merchant-web and customer-web on their own ports
   and stops them when the run ends.

Results are in `frontend/e2e/playwright-report/` (HTML). A failed test keeps a trace and a
screenshot in `frontend/e2e/test-results/`; open a trace with
`pnpm --dir frontend --filter @emi-copilot/e2e exec playwright show-trace <trace.zip>`.

## Ports and data (kept apart from development)

| What         | Where                                                                                                                                                                                              |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Database     | `emi_copilot_e2e` in the Compose PostgreSQL (host port `POSTGRES_HOST_PORT`, 55432 by default). The development database `emi_copilot` and the test database `emi_copilot_test` are never touched. |
| Backend      | `http://127.0.0.1:8010`, one uvicorn worker, no reload                                                                                                                                             |
| merchant-web | `http://127.0.0.1:5180`, Vite with `/api` proxied to 8010 (`MERCHANT_WEB_PORT`, `MERCHANT_WEB_API_PROXY_TARGET`)                                                                                   |
| customer-web | `http://127.0.0.1:5181`, Vite with `/api` proxied to 8010 (`CUSTOMER_WEB_PORT`, `CUSTOMER_WEB_API_PROXY_TARGET`); the backend gets `CUSTOMER_WEB_BASE_URL` set to it, so every QR link opens here  |

Ports 8000 and 5173 (developer servers) and 8001 and 5174 (Layer 3) stay free for their owners.
Playwright refuses to start if 8010, 5180 or 5181 is already taken, rather than testing someone
else's server. Override them with
`make e2e E2E_BACKEND_PORT=8020 E2E_MERCHANT_WEB_PORT=5190 E2E_CUSTOMER_WEB_PORT=5191`.

## What is mocked

- **MockPaymentGatewayAdapter** (`PAYMENT_GATEWAY_MODE=mock`): offers, payment links and payment
  reports are simulated; no request leaves the machine.
- **MockCustomerSimulator** (`MOCK_CUSTOMER_SIMULATOR_ENABLED=true`): stands in for the customer's
  phone. The tests pair a second device through the API (the browser's token lives only in page
  memory) and call its two endpoints: agree to the no-cost 6-month plan, and pay the Mock link.
- **Mock OTP sender** (`MOCK_CONSENT_OTP_CODE=123456`): the customer's consent OTP is always
  `123456` and goes to the Mock phone ending 42. It is never a real code.
- **Seed data:** the synthetic DESIGN_SPEC section 4 week, relative to the current time.
- **Pairing PIN:** `make e2e` seeds the throwaway PIN `123456` into the throwaway e2e database and
  hands it to the tests as `E2E_MERCHANT_PIN`. It is not a real shop's PIN.
- **Pairing rate limit:** raised to 100 a minute for the backend under test, because every test
  pairs from 127.0.0.1.

## What the tests cover

- **`tablet` project (1024 x 768), `merchantTabletHappyPath.spec.ts`:** pair (M1); the seeded
  counter list (M2); the seeded week's report with both panels and the brand-rep clipboard text
  (M5); start a sale and see its QR code (M3); "Ready to pay" with the plan's figures arriving
  live on the event stream; the EDC steps (M4); payment link, Mock payment and a
  server-confirmed "Paid". No customer finance or progress word appears on M2, M3 or M4.
- **`tablet` project, `merchantTabletTamil.spec.ts`:** the sidebar switch turns M2 and M5 into
  Tamil with no raw translation keys.
- **`phone` project (360 x 800), `merchantPhone.spec.ts`:** M3 shows the whole QR code without
  sideways scrolling, then the agreed plan totals; M8 reads the weekly message in Tamil.

- **`customerPhone` project (360 x 800, touch), `customerHappyPath.spec.ts`:** a tablet context
  pairs and starts a sale on M2; the phone opens its QR link (the token leaves the address bar),
  then C1, C2 (₹3,000), C3 Allow, C4 with the three design plans and bands (cardless first),
  C6 (₹3,000 a month, 36.7%, "ask the shop"), C7, C9 with one wrong OTP ("2 tries left") and
  the Mock OTP, C10 with an `EMI-` reference. Meanwhile M3 turns to "Ready to pay" live and
  never shows the customer's finances.
- **`customerPhone` project, `customerTamil.spec.ts`:** the same path with Tamil chosen on C1;
  every screen is in Tamil to the receipt (no raw keys, no English interface words).
- **`customerPhone` project, `customerSkipComfort.spec.ts`:** skipping the comfort check lists
  every plan without bands; a used QR link and a reloaded page show "Ask the shop for a new QR".

Every screen above also gets an axe check with zero violations allowed; every customer screen is
also checked for sideways scrolling at 360 px.

**Order.** The run uses one worker. The happy path checks the seeded week's numbers
(120 / 96 / 88 / 51 / 44) **before** it starts its own sale, which would add to the week. The
`phone` and `customerPhone` projects also start sales (and the customer's add funnel stages and
consent), so they declare a dependency on `tablet` and always run after it. Run the tests through `make e2e`, which reseeds a fresh database every time.
