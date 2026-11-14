/** Problem code used when the request never reached the server, for example the shop is offline. */
export const NETWORK_UNAVAILABLE_CODE = 'NETWORK_UNAVAILABLE';

/** Problem code used when a success answer had no body where one was expected. */
export const UNEXPECTED_RESPONSE_CODE = 'UNEXPECTED_RESPONSE';

/** The merchant token is missing, expired or revoked; the app must pair again. */
export const MERCHANT_AUTHENTICATION_REQUIRED_CODE = 'MERCHANT_AUTHENTICATION_REQUIRED';

// A failed API call as the screens see it: HTTP status, the stable problem code (mapped to
// translated text, never the English detail), the Retry-After seconds when the server sent them,
// and whether the server answered with a problem+json body (a definite answer from the API).
export class MerchantApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryAfterInSeconds: number | undefined;
  readonly hasProblemBody: boolean;

  constructor(status: number, code: string, retryAfterInSeconds?: number, hasProblemBody = false) {
    super(`Merchant API call failed with ${code} (${status})`);
    this.name = 'MerchantApiError';
    this.status = status;
    this.code = code;
    this.retryAfterInSeconds = retryAfterInSeconds;
    this.hasProblemBody = hasProblemBody;
  }
}

// Gives the problem code of any error a query or mutation raised; undefined for non-API errors.
export function readMerchantApiErrorCode(error: unknown): string | undefined {
  return error instanceof MerchantApiError ? error.code : undefined;
}

// True when the client cannot tell whether the server acted on a request: it never got an answer,
// a success came back unreadable, or a 5xx came without a problem body (a proxy or a crash). Any
// problem+json answer is definite, whatever its status.
export function isRequestOutcomeUnknown(error: unknown): boolean {
  if (!(error instanceof MerchantApiError)) return true;
  if (error.code === NETWORK_UNAVAILABLE_CODE || error.code === UNEXPECTED_RESPONSE_CODE) {
    return true;
  }
  return error.status >= 500 && !error.hasProblemBody;
}
