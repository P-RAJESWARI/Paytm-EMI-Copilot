import { describe, expect, it } from 'vitest';

import {
  createFakeCustomerBackend,
  jsonResponse,
  networkFailure,
  problemResponse,
  type FakeRoutes,
} from '../../../testing/fakeCustomerBackend';
import { CustomerApiError } from './customerApiError';
import {
  buildFixtureConsentedPlan,
  buildFixtureExplanation,
  FIXTURE_ALTERNATIVES_FOR_NO_COST_PLAN,
  FIXTURE_COMFORT_CHECK_COMPLETED,
  FIXTURE_NO_COST_PLAN,
  FIXTURE_PLANS_AT_DESIGN_BUDGET,
  FIXTURE_SESSION,
} from './fixtureCustomerFlowData';
import { HttpCustomerFlowApi } from './HttpCustomerFlowApi';

const SESSION_PATH = '/api/v1/customer-sessions/fixture-customer-session-4821';
const CONSENTED_PLAN = buildFixtureConsentedPlan(FIXTURE_NO_COST_PLAN);
const RECEIPT = {
  status: 'READY_TO_PAY',
  reference: 'EMI-2611-0042',
  phoneLastTwoDigits: '42',
  consentedAt: '2026-11-15T09:30:00Z',
  coolingOffNoticeStatus: 'PLACEHOLDER',
  plan: CONSENTED_PLAN,
};

const ROUTES: FakeRoutes = {
  'POST /api/v1/customer-sessions': () => jsonResponse(FIXTURE_SESSION, 201),
  'PUT /api/v1/customer-sessions/{customerSessionId}/budget': () =>
    jsonResponse({ monthlyBudgetInPaise: 300000, hasCustomerConfirmed: true }),
  'POST /api/v1/customer-sessions/{customerSessionId}/comfort-check': () =>
    jsonResponse(FIXTURE_COMFORT_CHECK_COMPLETED),
  'GET /api/v1/customer-sessions/{customerSessionId}/plans': () =>
    jsonResponse(FIXTURE_PLANS_AT_DESIGN_BUDGET),
  'POST /api/v1/customer-sessions/{customerSessionId}/alternatives': () =>
    jsonResponse(FIXTURE_ALTERNATIVES_FOR_NO_COST_PLAN),
  'POST /api/v1/customer-sessions/{customerSessionId}/explanation': () =>
    jsonResponse(buildFixtureExplanation(FIXTURE_NO_COST_PLAN, 'ta')),
  'POST /api/v1/customer-sessions/{customerSessionId}/consent/otp': () =>
    jsonResponse({
      phoneLastTwoDigits: '42',
      expiresAt: '2026-11-15T09:35:00Z',
      resendAvailableAt: '2026-11-15T09:30:30Z',
      attemptsRemaining: 3,
    }),
  'POST /api/v1/customer-sessions/{customerSessionId}/consent': () =>
    jsonResponse(
      {
        consentId: 'consent-1',
        reference: 'EMI-2611-0042',
        consentedAt: '2026-11-15T09:30:00Z',
        status: 'READY_TO_PAY',
        plan: CONSENTED_PLAN,
      },
      201,
    ),
  'GET /api/v1/customer-sessions/{customerSessionId}/receipt': () => jsonResponse(RECEIPT),
};

// Builds the HTTP adapter over a fake backend with the given routes.
function createApiOver(routes: FakeRoutes = ROUTES) {
  const fakeBackend = createFakeCustomerBackend(routes);
  const customerFlowApi = new HttpCustomerFlowApi({
    baseUrl: 'http://customer.test',
    fetchFunction: fakeBackend.fetchFunction,
  });
  return { fakeBackend, customerFlowApi };
}

// Opens a session through the adapter, as C1 does.
async function createApiWithOpenSession(routes: FakeRoutes = ROUTES) {
  const created = createApiOver(routes);
  await created.customerFlowApi.startSession('qr-token-1');
  return created;
}

describe('HttpCustomerFlowApi: the session token', () => {
  it('exchanges the QR once, keeps the token out of the answer and sends it on later calls', async () => {
    const { fakeBackend, customerFlowApi } = createApiOver();

    const session = await customerFlowApi.startSession('qr-token-1');
    await customerFlowApi.listPlans();

    expect(session).not.toHaveProperty('sessionToken');
    expect(session.shopName).toBe('Ravi Electronics');
    const [exchange, plansRequest] = fakeBackend.recordedRequests;
    expect(exchange?.body).toEqual({ qrToken: 'qr-token-1' });
    expect(exchange?.headers.has('X-Customer-Session-Token')).toBe(false);
    expect(exchange?.headers.get('X-Correlation-Id')).toMatch(/^[0-9a-f-]{36}$/);
    expect(plansRequest?.path).toBe(`${SESSION_PATH}/plans`);
    expect(plansRequest?.headers.get('X-Customer-Session-Token')).toBe('fixture-session-token');
  });

  it('refuses every call before a session is open, as a lost session, without any request', async () => {
    const { fakeBackend, customerFlowApi } = createApiOver();

    await expect(customerFlowApi.getReceipt()).rejects.toMatchObject({
      status: 401,
      code: 'CUSTOMER_SESSION_TOKEN_INVALID',
    });
    expect(fakeBackend.recordedRequests).toEqual([]);
  });
});

describe('HttpCustomerFlowApi: requests in the contract shape', () => {
  it('sends the budget, the comfort answer and the alternatives offer', async () => {
    const { fakeBackend, customerFlowApi } = await createApiWithOpenSession();

    await customerFlowApi.confirmBudget(300000);
    const comfortCheck = await customerFlowApi.answerComfortCheck(true);
    const alternatives = await customerFlowApi.findAlternatives('mock-offer-no-cost-6m');

    expect(comfortCheck).toEqual(FIXTURE_COMFORT_CHECK_COMPLETED);
    expect(alternatives.alternatives).toHaveLength(3);
    expect(
      fakeBackend.recordedRequests
        .slice(1)
        .map(({ method, path, body }) => ({ method, path, body })),
    ).toEqual([
      {
        method: 'PUT',
        path: `${SESSION_PATH}/budget`,
        body: { monthlyBudgetInPaise: 300000, hasCustomerConfirmed: true },
      },
      {
        method: 'POST',
        path: `${SESSION_PATH}/comfort-check`,
        body: { hasCustomerConsented: true },
      },
      {
        method: 'POST',
        path: `${SESSION_PATH}/alternatives`,
        body: { offerId: 'mock-offer-no-cost-6m' },
      },
    ]);
  });

  it('asks for the explanation in the chosen language', async () => {
    const { fakeBackend, customerFlowApi } = await createApiWithOpenSession();

    const explanation = await customerFlowApi.explainPlan('mock-offer-no-cost-6m', 'ta');

    expect(explanation.language).toBe('ta');
    const explanationRequest = fakeBackend.recordedRequests.at(-1);
    expect(explanationRequest?.headers.get('Accept-Language')).toBe('ta');
    expect(explanationRequest?.body).toEqual({ offerId: 'mock-offer-no-cost-6m' });
  });

  it('records consent with the Idempotency-Key, the language, the figures shown and the agreement', async () => {
    const { fakeBackend, customerFlowApi } = await createApiWithOpenSession();

    const otpChallenge = await customerFlowApi.requestConsentOtp();
    const confirmation = await customerFlowApi.giveConsent(
      {
        offerId: 'mock-offer-no-cost-6m',
        shownMonthlyInstallmentInPaise: 366667,
        shownTotalPayableInPaise: 2200000,
        otp: '123456',
      },
      'consent-key-1',
      'ta',
    );
    const receipt = await customerFlowApi.getReceipt();

    expect(otpChallenge.attemptsRemaining).toBe(3);
    expect(confirmation.reference).toBe('EMI-2611-0042');
    expect(receipt.status).toBe('READY_TO_PAY');
    const consentRequest = fakeBackend.recordedRequests.at(-2);
    expect(consentRequest?.path).toBe(`${SESSION_PATH}/consent`);
    expect(consentRequest?.headers.get('Idempotency-Key')).toBe('consent-key-1');
    expect(consentRequest?.headers.get('Accept-Language')).toBe('ta');
    expect(consentRequest?.body).toEqual({
      offerId: 'mock-offer-no-cost-6m',
      shownMonthlyInstallmentInPaise: 366667,
      shownTotalPayableInPaise: 2200000,
      otp: '123456',
      hasAgreedToPlan: true,
    });
  });
});

describe('HttpCustomerFlowApi: problems', () => {
  it('reads OTP_INCORRECT with the tries left, and Retry-After on 429', async () => {
    const { customerFlowApi } = await createApiWithOpenSession({
      ...ROUTES,
      'POST /api/v1/customer-sessions/{customerSessionId}/consent': () =>
        problemResponse(422, 'OTP_INCORRECT', {}, { attemptsRemaining: 2 }),
      'POST /api/v1/customer-sessions/{customerSessionId}/consent/otp': () =>
        problemResponse(429, 'RATE_LIMITED', { 'Retry-After': '24' }),
    });

    const consentError = await customerFlowApi
      .giveConsent(
        {
          offerId: 'mock-offer-no-cost-6m',
          shownMonthlyInstallmentInPaise: 366667,
          shownTotalPayableInPaise: 2200000,
          otp: '000000',
        },
        'consent-key-2',
        'en',
      )
      .catch((error: unknown) => error);

    expect(consentError).toBeInstanceOf(CustomerApiError);
    expect(consentError).toMatchObject({
      code: 'OTP_INCORRECT',
      attemptsRemaining: 2,
      hasProblemBody: true,
    });
    await expect(customerFlowApi.requestConsentOtp()).rejects.toMatchObject({
      status: 429,
      retryAfterInSeconds: 24,
    });
  });

  it('turns a reused QR into CUSTOMER_QR_TOKEN_INVALID and a lost signal into NETWORK_UNAVAILABLE', async () => {
    const reusedQr = createApiOver({
      'POST /api/v1/customer-sessions': () => problemResponse(401, 'CUSTOMER_QR_TOKEN_INVALID'),
    });
    const offline = createApiOver({ 'POST /api/v1/customer-sessions': () => networkFailure() });

    await expect(reusedQr.customerFlowApi.startSession('used')).rejects.toMatchObject({
      status: 401,
      code: 'CUSTOMER_QR_TOKEN_INVALID',
    });
    await expect(offline.customerFlowApi.startSession('any')).rejects.toMatchObject({
      status: 0,
      code: 'NETWORK_UNAVAILABLE',
    });
  });
});
