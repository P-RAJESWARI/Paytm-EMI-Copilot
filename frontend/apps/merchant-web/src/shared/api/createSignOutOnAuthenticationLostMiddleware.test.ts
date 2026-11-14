import { createBackendApiClient } from '@emi-copilot/api-client';
import { describe, expect, it, vi } from 'vitest';

import {
  createSignOutOnAuthenticationLostMiddleware,
  readJsonBodyOfCopy,
} from './createSignOutOnAuthenticationLostMiddleware';

// Sends GET /merchants/me through a generated client whose fetch gives the answer.
async function requestProfileAnswering(response: Response, onAuthenticationLost: () => void) {
  const apiClient = createBackendApiClient({
    baseUrl: 'http://localhost',
    fetch: () => Promise.resolve(response),
  });
  apiClient.use(createSignOutOnAuthenticationLostMiddleware(onAuthenticationLost));
  return apiClient.GET('/api/v1/merchants/me');
}

describe('createSignOutOnAuthenticationLostMiddleware', () => {
  it('signs out on 401 MERCHANT_AUTHENTICATION_REQUIRED and leaves the body readable', async () => {
    const onAuthenticationLost = vi.fn();
    const response = new Response(JSON.stringify({ code: 'MERCHANT_AUTHENTICATION_REQUIRED' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });

    const result = await requestProfileAnswering(response, onAuthenticationLost);

    expect(onAuthenticationLost).toHaveBeenCalledOnce();
    expect(result.error).toEqual({ code: 'MERCHANT_AUTHENTICATION_REQUIRED' });
  });

  it('keeps the session on a wrong PIN (401 with another code) and on other statuses', async () => {
    const onAuthenticationLost = vi.fn();

    await requestProfileAnswering(
      new Response(JSON.stringify({ code: 'INVALID_PAIRING_CREDENTIALS' }), { status: 401 }),
      onAuthenticationLost,
    );
    await requestProfileAnswering(new Response('not json', { status: 401 }), onAuthenticationLost);
    await requestProfileAnswering(new Response('{}', { status: 200 }), onAuthenticationLost);

    expect(onAuthenticationLost).not.toHaveBeenCalled();
  });

  it('reads a JSON copy and gives undefined for a body that is not JSON', async () => {
    await expect(readJsonBodyOfCopy(new Response('{"a":1}'))).resolves.toEqual({ a: 1 });
    await expect(readJsonBodyOfCopy(new Response('plain'))).resolves.toBeUndefined();
  });
});
