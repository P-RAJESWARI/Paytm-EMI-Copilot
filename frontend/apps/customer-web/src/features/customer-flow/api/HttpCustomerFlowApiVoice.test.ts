import { describe, expect, it } from 'vitest';

import {
  createFakeCustomerBackend,
  jsonResponse,
  problemResponse,
  type FakeRoutes,
} from '../../../testing/fakeCustomerBackend';
import { CustomerApiError } from './customerApiError';
import { FIXTURE_SESSION } from './fixtureCustomerFlowData';
import { HttpCustomerFlowApi } from './HttpCustomerFlowApi';

const SESSION_PATH = '/api/v1/customer-sessions/fixture-customer-session-4821';
const TEACH_BACK_ANSWER = {
  result: 'CLOSE_ENOUGH',
  title: 'That is right',
  body: 'You will pay ₹3,667 every month for 6 months.',
  heardText: null,
  highlightedAmounts: [{ kind: 'MONTHLY_INSTALLMENT', amountInPaise: 366700 }],
};

const ROUTES: FakeRoutes = {
  'POST /api/v1/customer-sessions': () => jsonResponse(FIXTURE_SESSION, 201),
  'POST /api/v1/customer-sessions/{customerSessionId}/speech/transcriptions': () =>
    jsonResponse({
      transcript: 'three thousand',
      recognisedAmountInPaise: 300000,
      isLikelyMisheard: false,
    }),
  'POST /api/v1/customer-sessions/{customerSessionId}/speech/synthesis': () =>
    new Response('mp3-bytes', {
      status: 200,
      headers: { 'Content-Type': 'audio/mpeg' },
    }),
  'POST /api/v1/customer-sessions/{customerSessionId}/teach-back': () =>
    jsonResponse(TEACH_BACK_ANSWER),
};

// Builds the HTTP adapter over a fake backend and opens a session, as C1 does.
async function createApiWithOpenSession(routes: FakeRoutes = ROUTES) {
  const fakeBackend = createFakeCustomerBackend(routes);
  const customerFlowApi = new HttpCustomerFlowApi({
    baseUrl: 'http://customer.test',
    fetchFunction: fakeBackend.fetchFunction,
  });
  await customerFlowApi.startSession('qr-token-1');
  return { fakeBackend, customerFlowApi };
}

describe('HttpCustomerFlowApi: Layer 4 voice and teach-back', () => {
  it('sends the raw recording with its content type, the purpose and the session token', async () => {
    const { fakeBackend, customerFlowApi } = await createApiWithOpenSession();

    const transcription = await customerFlowApi.transcribeSpeech(
      new Blob(['audio'], { type: 'audio/ogg' }),
      'BUDGET',
      'ta',
    );

    expect(transcription.recognisedAmountInPaise).toBe(300000);
    const request = fakeBackend.recordedRequests.at(-1);
    expect(request?.path).toBe(`${SESSION_PATH}/speech/transcriptions?purpose=BUDGET`);
    expect(request?.headers.get('Content-Type')).toBe('audio/ogg');
    expect(request?.headers.get('X-Customer-Session-Token')).toBe('fixture-session-token');
    expect(request?.headers.get('X-Correlation-Id')).toBeTruthy();
    expect(request?.headers.get('Accept-Language')).toBe('ta');
    expect(request?.body).toBe('audio');
  });

  it('defaults a recording without a type to audio/webm', async () => {
    const { fakeBackend, customerFlowApi } = await createApiWithOpenSession();

    await customerFlowApi.transcribeSpeech(new Blob(['audio']), 'TEACH_BACK', 'en');

    expect(fakeBackend.recordedRequests.at(-1)?.headers.get('Content-Type')).toBe('audio/webm');
  });

  it('reads the spoken explanation as a Blob', async () => {
    const { fakeBackend, customerFlowApi } = await createApiWithOpenSession();

    const audio = await customerFlowApi.synthesiseExplanation('explanation-1');

    expect(await audio.text()).toBe('mp3-bytes');
    expect(fakeBackend.recordedRequests.at(-1)?.body).toEqual({ explanationId: 'explanation-1' });
    expect(fakeBackend.recordedRequests.at(-1)?.headers.get('X-Customer-Session-Token')).toBe(
      'fixture-session-token',
    );
  });

  it('sends the teach-back answer with the language and reads the result', async () => {
    const { fakeBackend, customerFlowApi } = await createApiWithOpenSession();

    const outcome = await customerFlowApi.checkTeachBack('offer-1', 'I pay 3,667', 'ta');

    expect(outcome.result).toBe('CLOSE_ENOUGH');
    const request = fakeBackend.recordedRequests.at(-1);
    expect(request?.body).toEqual({ offerId: 'offer-1', answerText: 'I pay 3,667' });
    expect(request?.headers.get('Accept-Language')).toBe('ta');
  });

  it('turns a problem answer into its stable code, and an unreadable one into a fallback', async () => {
    const { customerFlowApi } = await createApiWithOpenSession({
      ...ROUTES,
      'POST /api/v1/customer-sessions/{customerSessionId}/speech/synthesis': () =>
        problemResponse(404, 'EXPLANATION_NOT_FOUND'),
      'POST /api/v1/customer-sessions/{customerSessionId}/teach-back': () =>
        new Response('<html>gateway</html>', { status: 504 }),
    });

    await expect(customerFlowApi.synthesiseExplanation('missing')).rejects.toMatchObject({
      status: 404,
      code: 'EXPLANATION_NOT_FOUND',
    });
    await expect(customerFlowApi.checkTeachBack('offer-1', 'x', 'en')).rejects.toMatchObject({
      status: 504,
      hasProblemBody: false,
    });
  });

  it('refuses without sending when no session is open', async () => {
    const fakeBackend = createFakeCustomerBackend(ROUTES);
    const customerFlowApi = new HttpCustomerFlowApi({
      baseUrl: 'http://customer.test',
      fetchFunction: fakeBackend.fetchFunction,
    });

    await expect(customerFlowApi.synthesiseExplanation('explanation-1')).rejects.toBeInstanceOf(
      CustomerApiError,
    );
    expect(fakeBackend.recordedRequests).toEqual([]);
  });
});
