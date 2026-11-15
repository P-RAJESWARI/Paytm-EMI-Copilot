import { describe, expect, it } from 'vitest';

import {
  CustomerApiError,
  isRequestOutcomeUnknown,
  isSessionLostError,
  readCustomerApiErrorCode,
} from './customerApiError';
import { readApiData } from './readApiData';

// Builds an openapi-fetch style result around a Response.
function apiResult<Data>(response: Response, data?: Data, error?: unknown) {
  return Promise.resolve({ data, error, response });
}

describe('readApiData', () => {
  it('gives the body of a successful call', async () => {
    await expect(
      readApiData(apiResult(new Response('{}'), { reference: 'EMI-1' })),
    ).resolves.toEqual({ reference: 'EMI-1' });
  });

  it('throws the code, Retry-After seconds and tries left of a refusal', async () => {
    const response = new Response('{}', { status: 422, headers: { 'Retry-After': '30' } });

    const error = await readApiData(
      apiResult(response, undefined, { code: 'OTP_INCORRECT', attemptsRemaining: 2 }),
    ).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(CustomerApiError);
    expect(error).toMatchObject({
      status: 422,
      code: 'OTP_INCORRECT',
      retryAfterInSeconds: 30,
      hasProblemBody: true,
      attemptsRemaining: 2,
    });
  });

  it('ignores a Retry-After date, a tries-left that is not whole and a body that is not a problem', async () => {
    const response = new Response('', {
      status: 502,
      headers: { 'Retry-After': 'Wed, 21 Oct 2026 07:28:00 GMT' },
    });

    await expect(
      readApiData(apiResult(response, undefined, { attemptsRemaining: 'two' })),
    ).rejects.toMatchObject({
      code: 'UNEXPECTED_ERROR',
      retryAfterInSeconds: undefined,
      attemptsRemaining: undefined,
      hasProblemBody: false,
    });
    await expect(readApiData(apiResult(response, undefined, null))).rejects.toMatchObject({
      attemptsRemaining: undefined,
    });
  });

  it('turns a request that never left into NETWORK_UNAVAILABLE and passes other failures on', async () => {
    const abortError = new DOMException('Aborted', 'AbortError');

    await expect(
      readApiData(Promise.reject(new TypeError('Failed to fetch'))),
    ).rejects.toMatchObject({ status: 0, code: 'NETWORK_UNAVAILABLE' });
    await expect(readApiData(Promise.reject(abortError))).rejects.toBe(abortError);
  });

  it('refuses a success answer without the expected body', async () => {
    await expect(readApiData(apiResult(new Response(null, { status: 200 })))).rejects.toMatchObject(
      { code: 'UNEXPECTED_RESPONSE' },
    );
  });
});

describe('customer API error helpers', () => {
  it('reads the code only from API errors', () => {
    expect(readCustomerApiErrorCode(new CustomerApiError(409, 'SHOWN_PLAN_CHANGED'))).toBe(
      'SHOWN_PLAN_CHANGED',
    );
    expect(readCustomerApiErrorCode(new Error('other'))).toBeUndefined();
  });

  it('treats a used QR, a dead token and a foreign session id as a lost session', () => {
    expect(isSessionLostError(new CustomerApiError(401, 'CUSTOMER_QR_TOKEN_INVALID'))).toBe(true);
    expect(isSessionLostError(new CustomerApiError(401, 'CUSTOMER_SESSION_TOKEN_INVALID'))).toBe(
      true,
    );
    expect(isSessionLostError(new CustomerApiError(404, 'CUSTOMER_SESSION_NOT_FOUND'))).toBe(true);
    expect(isSessionLostError(new CustomerApiError(422, 'OTP_INCORRECT'))).toBe(false);
    expect(isSessionLostError(new Error('other'))).toBe(false);
  });

  it('knows when a request outcome is unknown', () => {
    expect(isRequestOutcomeUnknown(new CustomerApiError(0, 'NETWORK_UNAVAILABLE'))).toBe(true);
    expect(isRequestOutcomeUnknown(new CustomerApiError(201, 'UNEXPECTED_RESPONSE'))).toBe(true);
    expect(isRequestOutcomeUnknown(new CustomerApiError(502, 'UNEXPECTED_ERROR'))).toBe(true);
    expect(isRequestOutcomeUnknown(new Error('other'))).toBe(true);
    expect(
      isRequestOutcomeUnknown(
        new CustomerApiError(504, 'PAYMENT_GATEWAY_TIMEOUT', { hasProblemBody: true }),
      ),
    ).toBe(false);
    expect(isRequestOutcomeUnknown(new CustomerApiError(422, 'OTP_INCORRECT'))).toBe(false);
  });
});
