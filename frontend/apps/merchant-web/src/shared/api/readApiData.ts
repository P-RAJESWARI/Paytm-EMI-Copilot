import { readProblemCode } from '@emi-copilot/api-client';

import {
  MerchantApiError,
  NETWORK_UNAVAILABLE_CODE,
  UNEXPECTED_RESPONSE_CODE,
} from './merchantApiError';

/** The shape every generated client call resolves to (openapi-fetch's FetchResponse). */
export interface ApiCallResult<Data> {
  data?: Data;
  error?: unknown;
  response: Response;
}

const FALLBACK_PROBLEM_CODE = 'UNEXPECTED_ERROR';

// Reads Retry-After as whole seconds; an HTTP-date or anything else gives undefined.
function readRetryAfterInSeconds(response: Response): number | undefined {
  const headerValue = response.headers.get('Retry-After');
  if (headerValue === null || !/^\d+$/.test(headerValue.trim())) return undefined;
  return Number(headerValue.trim());
}

// Awaits a generated client call and gives its body, or throws a MerchantApiError with the problem
// code and whether a problem body came; no answer at all becomes NETWORK_UNAVAILABLE.
export async function readApiData<Data>(apiCall: Promise<ApiCallResult<Data>>): Promise<Data> {
  let result: ApiCallResult<Data>;
  try {
    result = await apiCall;
  } catch (error) {
    if (error instanceof TypeError) throw new MerchantApiError(0, NETWORK_UNAVAILABLE_CODE);
    throw error;
  }
  const { data, error, response } = result;
  if (!response.ok) {
    const problemCode = readProblemCode(error);
    throw new MerchantApiError(
      response.status,
      problemCode ?? FALLBACK_PROBLEM_CODE,
      readRetryAfterInSeconds(response),
      problemCode !== undefined,
    );
  }
  if (data === undefined) throw new MerchantApiError(response.status, UNEXPECTED_RESPONSE_CODE);
  return data;
}
