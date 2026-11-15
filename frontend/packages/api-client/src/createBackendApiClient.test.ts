import { describe, expect, it, vi } from 'vitest';

import { createBackendApiClient } from './createBackendApiClient';
import { CORRELATION_ID_HEADER } from './middleware/correlationIdMiddleware';
import { CUSTOMER_SESSION_TOKEN_HEADER } from './middleware/customerSessionTokenMiddleware';

const UUID_VERSION_4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

// A fetch stand-in that records each request and answers with an empty JSON object.
function createRecordingFetch() {
  const sentRequests: Request[] = [];
  const fetch = vi.fn((request: Request) => {
    sentRequests.push(request);
    return Promise.resolve(
      new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );
  });
  return { fetch, sentRequests };
}

// Gives the request recorded at a position, failing clearly if it was not sent.
function requestAt(sentRequests: Request[], position: number): Request {
  const request = sentRequests[position];
  if (request === undefined) throw new Error(`No request was sent at position ${position}`);
  return request;
}

describe('createBackendApiClient', () => {
  it('sends the bearer token from the getter and a correlation id', async () => {
    const { fetch, sentRequests } = createRecordingFetch();
    const client = createBackendApiClient({
      baseUrl: 'http://api.test',
      getAccessToken: () => 'merchant-token',
      createCorrelationId: () => 'correlation-1',
      fetch,
    });

    await client.GET('/api/v1/merchants/me');

    const request = requestAt(sentRequests, 0);
    expect(request.url).toBe('http://api.test/api/v1/merchants/me');
    expect(request.headers.get('Authorization')).toBe('Bearer merchant-token');
    expect(request.headers.get(CORRELATION_ID_HEADER)).toBe('correlation-1');
  });

  it('reads the token on every request, so a new pairing is picked up', async () => {
    const { fetch, sentRequests } = createRecordingFetch();
    let currentToken: string | undefined = undefined;
    const client = createBackendApiClient({
      baseUrl: 'http://api.test',
      getAccessToken: () => currentToken,
      fetch,
    });

    await client.GET('/api/v1/products');
    currentToken = 'fresh-token';
    await client.GET('/api/v1/products');

    expect(requestAt(sentRequests, 0).headers.has('Authorization')).toBe(false);
    expect(requestAt(sentRequests, 1).headers.get('Authorization')).toBe('Bearer fresh-token');
  });

  it('sends no Authorization header for an empty token or without a getter', async () => {
    const { fetch, sentRequests } = createRecordingFetch();
    const clientWithEmptyToken = createBackendApiClient({
      baseUrl: 'http://api.test',
      getAccessToken: () => '',
      fetch,
    });
    const clientWithoutGetter = createBackendApiClient({ baseUrl: 'http://api.test', fetch });

    await clientWithEmptyToken.GET('/health');
    await clientWithoutGetter.POST('/api/v1/merchants/pairing', {
      body: { shopId: 'RAVI-0193', pin: '000000' },
    });

    expect(requestAt(sentRequests, 0).headers.has('Authorization')).toBe(false);
    expect(requestAt(sentRequests, 1).headers.has('Authorization')).toBe(false);
  });

  it('sends the customer session token from its getter once the phone holds one', async () => {
    const { fetch, sentRequests } = createRecordingFetch();
    let customerSessionToken: string | undefined = undefined;
    const client = createBackendApiClient({
      baseUrl: 'http://api.test',
      getCustomerSessionToken: () => customerSessionToken,
      fetch,
    });

    await client.POST('/api/v1/customer-sessions', { body: { qrToken: 'qr-token' } });
    customerSessionToken = 'customer-session-token';
    await client.GET('/api/v1/customer-sessions/{customerSessionId}/plans', {
      params: { path: { customerSessionId: 'session-1' } },
    });

    expect(requestAt(sentRequests, 0).headers.has(CUSTOMER_SESSION_TOKEN_HEADER)).toBe(false);
    const plansRequest = requestAt(sentRequests, 1);
    expect(plansRequest.headers.get(CUSTOMER_SESSION_TOKEN_HEADER)).toBe('customer-session-token');
    expect(plansRequest.headers.has('Authorization')).toBe(false);
  });

  it('keeps a customer session token the caller set and skips an empty one', async () => {
    const { fetch, sentRequests } = createRecordingFetch();
    const clientWithEmptyToken = createBackendApiClient({
      baseUrl: 'http://api.test',
      getCustomerSessionToken: () => '',
      fetch,
    });
    const clientWithToken = createBackendApiClient({
      baseUrl: 'http://api.test',
      getCustomerSessionToken: () => 'held-token',
      fetch,
    });

    await clientWithEmptyToken.GET('/health');
    await clientWithToken.GET('/health', {
      headers: { [CUSTOMER_SESSION_TOKEN_HEADER]: 'explicit-token' },
    });

    expect(requestAt(sentRequests, 0).headers.has(CUSTOMER_SESSION_TOKEN_HEADER)).toBe(false);
    expect(requestAt(sentRequests, 1).headers.get(CUSTOMER_SESSION_TOKEN_HEADER)).toBe(
      'explicit-token',
    );
  });

  it('gives each request a different random UUID v4 correlation id by default', async () => {
    const { fetch, sentRequests } = createRecordingFetch();
    const client = createBackendApiClient({ baseUrl: 'http://api.test', fetch });

    await client.GET('/health');
    await client.GET('/health');

    const firstId = requestAt(sentRequests, 0).headers.get(CORRELATION_ID_HEADER) ?? '';
    const secondId = requestAt(sentRequests, 1).headers.get(CORRELATION_ID_HEADER) ?? '';
    expect(firstId).toMatch(UUID_VERSION_4);
    expect(secondId).toMatch(UUID_VERSION_4);
    expect(firstId).not.toBe(secondId);
  });

  it('keeps headers the caller set explicitly', async () => {
    const { fetch, sentRequests } = createRecordingFetch();
    const client = createBackendApiClient({
      baseUrl: 'http://api.test',
      getAccessToken: () => 'merchant-token',
      fetch,
    });

    await client.GET('/api/v1/merchants/me', {
      headers: { Authorization: 'Bearer explicit', [CORRELATION_ID_HEADER]: 'explicit-id' },
    });

    const request = requestAt(sentRequests, 0);
    expect(request.headers.get('Authorization')).toBe('Bearer explicit');
    expect(request.headers.get(CORRELATION_ID_HEADER)).toBe('explicit-id');
  });

  it('uses the global fetch and same-origin URLs by default', async () => {
    const { fetch, sentRequests } = createRecordingFetch();
    vi.stubGlobal('fetch', fetch);
    const client = createBackendApiClient();

    await client.GET('/health');

    expect(requestAt(sentRequests, 0).url).toBe(`${window.location.origin}/health`);
  });
});
