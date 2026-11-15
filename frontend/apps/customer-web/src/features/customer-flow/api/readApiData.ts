import { readProblemCode } from '@emi-copilot/api-client';

import {
  CustomerApiError,
  NETWORK_UNAVAILABLE_CODE,
  UNEXPECTED_RESPONSE_CODE,
} from './customerApiError';

/** The shape every openapi-fetch call resolves to (its FetchResponse). */
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

// Reads the OTP_INCORRECT extension member attemptsRemaining when it is a whole number.
function readAttemptsRemaining(errorBody: unknown): number | undefined {
  if (typeof errorBody !== 'object' || errorBody === null) return undefined;
  if (!('attemptsRemaining' in errorBody)) return undefined;
  const attemptsRemaining = errorBody.attemptsRemaining;
  return Number.isSafeInteger(attemptsRemaining) ? Number(attemptsRemaining) : undefined;
}

// Awaits an openapi-fetch call and gives its body, or throws a CustomerApiError with the problem
// code; no answer at all becomes NETWORK_UNAVAILABLE.
export async function readApiData<Data>(apiCall: Promise<ApiCallResult<Data>>): Promise<Data> {
  let result: ApiCallResult<Data>;
  try {
    result = await apiCall;
  } catch (error) {
    if (error instanceof TypeError) throw new CustomerApiError(0, NETWORK_UNAVAILABLE_CODE);
    throw error;
  }
  const { data, error, response } = result;
  if (!response.ok) {
    const problemCode = readProblemCode(error);
    throw new CustomerApiError(response.status, problemCode ?? FALLBACK_PROBLEM_CODE, {
      retryAfterInSeconds: readRetryAfterInSeconds(response),
      hasProblemBody: problemCode !== undefined,
      attemptsRemaining: readAttemptsRemaining(error),
    });
  }
  if (data === undefined) throw new CustomerApiError(response.status, UNEXPECTED_RESPONSE_CODE);
  return data;
}
