// Playwright config for the merchant and customer end-to-end paths (testing.md section 4). `make e2e`
// prepares the e2e database; Playwright then starts the backend, merchant-web and customer-web on
// their own ports and stops them at the end. Only localhost is contacted: the backend runs the Mock
// payment gateway and the Mock OTP sender.
import { fileURLToPath } from 'node:url';

import { defineConfig, devices } from '@playwright/test';

import {
  BACKEND_ORIGIN,
  BACKEND_PORT,
  CUSTOMER_WEB_ORIGIN,
  CUSTOMER_WEB_PORT,
  MERCHANT_WEB_ORIGIN,
  MERCHANT_WEB_PORT,
  MOCK_CONSENT_OTP_CODE,
  readEndToEndDatabaseUrl,
} from './support/endToEndSettings';

const BACKEND_DIRECTORY = fileURLToPath(new URL('../../backend', import.meta.url));
const MERCHANT_WEB_DIRECTORY = fileURLToPath(new URL('../apps/merchant-web', import.meta.url));
const CUSTOMER_WEB_DIRECTORY = fileURLToPath(new URL('../apps/customer-web', import.meta.url));

/** Starting uv and Vite cold can take a while on a first run. */
const SERVER_START_TIMEOUT_IN_MILLISECONDS = 120_000;

/** Several devices pair from 127.0.0.1 in one run; the default 10 a minute is for real shops. */
const END_TO_END_PAIRING_RATE_LIMIT = '100';

const desktopChromium = devices['Desktop Chrome'];

export default defineConfig({
  testDir: './tests',
  outputDir: './test-results',
  // One worker, in a declared order: the tablet path checks the seeded week before it starts a
  // sale, and the phone and customerPhone projects (which start sales, and the customer's also
  // adds funnel stages and consents) run only after the tablet project.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { outputFolder: './playwright-report', open: 'never' }]],
  use: {
    baseURL: MERCHANT_WEB_ORIGIN,
    locale: 'en-IN',
    timezoneId: 'Asia/Kolkata',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'tablet',
      testMatch: /merchantTablet.*\.spec\.ts$/,
      use: {
        ...desktopChromium,
        viewport: { width: 1024, height: 768 },
        permissions: ['clipboard-read', 'clipboard-write'],
      },
    },
    {
      name: 'phone',
      testMatch: /merchantPhone.*\.spec\.ts$/,
      dependencies: ['tablet'],
      use: {
        ...desktopChromium,
        viewport: { width: 360, height: 800 },
        hasTouch: true,
      },
    },
    {
      name: 'customerPhone',
      testMatch: /customer.*\.spec\.ts$/,
      dependencies: ['tablet'],
      use: {
        ...desktopChromium,
        baseURL: CUSTOMER_WEB_ORIGIN,
        viewport: { width: 360, height: 800 },
        hasTouch: true,
      },
    },
  ],
  webServer: [
    {
      name: 'backend',
      command: `uv run --locked uvicorn emi_copilot.main:create_application --factory --workers 1 --host 127.0.0.1 --port ${BACKEND_PORT}`,
      cwd: BACKEND_DIRECTORY,
      url: `${BACKEND_ORIGIN}/health`,
      reuseExistingServer: false,
      timeout: SERVER_START_TIMEOUT_IN_MILLISECONDS,
      env: {
        DATABASE_URL: readEndToEndDatabaseUrl(),
        PAYMENT_GATEWAY_MODE: 'mock',
        MOCK_CUSTOMER_SIMULATOR_ENABLED: 'true',
        MERCHANT_PAIRING_RATE_LIMIT_MAX_REQUESTS: END_TO_END_PAIRING_RATE_LIMIT,
        // The QR link of every sale opens the customer-web server below.
        CUSTOMER_WEB_BASE_URL: CUSTOMER_WEB_ORIGIN,
        MOCK_CONSENT_OTP_CODE,
        // Customer rate limits (QR exchange, OTP request, OTP check, consent): generous e2e
        // values go here once the backend names their settings; every test calls from 127.0.0.1.
        LOG_LEVEL: 'WARNING',
      },
    },
    {
      name: 'merchant-web',
      command: 'pnpm exec vite --host 127.0.0.1',
      cwd: MERCHANT_WEB_DIRECTORY,
      url: MERCHANT_WEB_ORIGIN,
      reuseExistingServer: false,
      timeout: SERVER_START_TIMEOUT_IN_MILLISECONDS,
      env: {
        MERCHANT_WEB_PORT: String(MERCHANT_WEB_PORT),
        MERCHANT_WEB_API_PROXY_TARGET: BACKEND_ORIGIN,
      },
    },
    {
      name: 'customer-web',
      command: 'pnpm exec vite --host 127.0.0.1',
      cwd: CUSTOMER_WEB_DIRECTORY,
      url: CUSTOMER_WEB_ORIGIN,
      reuseExistingServer: false,
      timeout: SERVER_START_TIMEOUT_IN_MILLISECONDS,
      env: {
        CUSTOMER_WEB_PORT: String(CUSTOMER_WEB_PORT),
        CUSTOMER_WEB_API_PROXY_TARGET: BACKEND_ORIGIN,
        // The real customer API, never the design-sample fixture.
        VITE_CUSTOMER_FLOW_API: 'http',
      },
    },
  ],
});
