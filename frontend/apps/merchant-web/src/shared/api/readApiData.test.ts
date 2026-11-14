import { describe, expect, it } from 'vitest';

import {
  isRequestOutcomeUnknown,
  MerchantApiError,
  readMerchantApiErrorCode,
} from './merchantApiError';
import { readApiData } from './readApiData';

// Builds a generated-client style result around a Response.
function apiResult<Data>(response: Response, data?: Data, error?: unknown) {
  return Promise.resolve({ data, error, response });
}

describe('readApiData', () => {
  it('gives the body of a successful call', async () => {
    await expect(readApiData(apiResult(new Response('{}'), { saleId: 'sale-1' }))).resolves.toEqual(
      {
        saleId: 'sale-1',
      },
    );
  });

  it('throws the problem code and the Retry-After seconds of a refusal', async () => {
    const response = new Response('{}', { status: 429, headers: { 'Retry-After': '840' } });

    const error = await readApiData(
      apiResult(response, undefined, { code: 'PAIRING_TEMPORARILY_LOCKED' }),
    ).catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(MerchantApiError);
    expect(error).toMatchObject({
      status: 429,
      code: 'PAIRING_TEMPORARILY_LOCKED',
      retryAfterInSeconds: 840,
      hasProblemBody: true,
    });
  });

  it('ignores a Retry-After that is not whole seconds and names a body-less refusal', async () => {
    const response = new Response('', {
      status: 500,
      headers: { 'Retry-After': 'Wed, 21 Oct 2026 07:28:00 GMT' },
    });

    await expect(readApiData(apiResult(response, undefined, ''))).rejects.toMatchObject({
      code: 'UNEXPECTED_ERROR',
      retryAfterInSeconds: undefined,
      hasProblemBody: false,
    });
  });

  it('turns a request that never reached the server into NETWORK_UNAVAILABLE', async () => {
    await expect(
      readApiData(Promise.reject(new TypeError('Failed to fetch'))),
    ).rejects.toMatchObject({
      status: 0,
      code: 'NETWORK_UNAVAILABLE',
    });
  });

  it('passes on any other failure unchanged', async () => {
    const abortError = new DOMException('Aborted', 'AbortError');

    await expect(readApiData(Promise.reject(abortError))).rejects.toBe(abortError);
  });

  it('refuses a success answer without the expected body', async () => {
    await expect(readApiData(apiResult(new Response(null, { status: 204 })))).rejects.toMatchObject(
      {
        code: 'UNEXPECTED_RESPONSE',
      },
    );
  });

  it('reads the code only from API errors', () => {
    expect(readMerchantApiErrorCode(new MerchantApiError(404, 'SALE_NOT_FOUND'))).toBe(
      'SALE_NOT_FOUND',
    );
    expect(readMerchantApiErrorCode(new Error('other'))).toBeUndefined();
  });
});

describe('isRequestOutcomeUnknown', () => {
  it('is unknown when no answer came, a success was unreadable or a 5xx had no problem body', () => {
    expect(isRequestOutcomeUnknown(new MerchantApiError(0, 'NETWORK_UNAVAILABLE'))).toBe(true);
    expect(isRequestOutcomeUnknown(new MerchantApiError(201, 'UNEXPECTED_RESPONSE'))).toBe(true);
    expect(isRequestOutcomeUnknown(new MerchantApiError(502, 'UNEXPECTED_ERROR'))).toBe(true);
    expect(isRequestOutcomeUnknown(new DOMException('Aborted', 'AbortError'))).toBe(true);
  });

  it('is definite for any problem+json answer, a 5xx included, and for a body-less 4xx', () => {
    const gatewayTimeout = new MerchantApiError(504, 'PAYMENT_GATEWAY_TIMEOUT', undefined, true);
    const linkFailed = new MerchantApiError(422, 'PAYMENT_LINK_CREATION_FAILED', undefined, true);

    expect(isRequestOutcomeUnknown(gatewayTimeout)).toBe(false);
    expect(isRequestOutcomeUnknown(linkFailed)).toBe(false);
    expect(isRequestOutcomeUnknown(new MerchantApiError(413, 'UNEXPECTED_ERROR'))).toBe(false);
  });
});
