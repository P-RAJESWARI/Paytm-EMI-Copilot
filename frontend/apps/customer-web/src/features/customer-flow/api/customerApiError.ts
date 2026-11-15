/** The request never reached the server, for example the phone lost its signal. */
export const NETWORK_UNAVAILABLE_CODE = 'NETWORK_UNAVAILABLE';
/** A success answer had no body where one was expected. */
export const UNEXPECTED_RESPONSE_CODE = 'UNEXPECTED_RESPONSE';
/** The QR was already used, expired or is not ours: ask the shop for a new QR. */
export const CUSTOMER_QR_TOKEN_INVALID_CODE = 'CUSTOMER_QR_TOKEN_INVALID';
/** The session token is missing, expired or replaced by a new scan: ask the shop for a new QR. */
export const CUSTOMER_SESSION_TOKEN_INVALID_CODE = 'CUSTOMER_SESSION_TOKEN_INVALID';
/** A valid token used with another session id; answered the same whether that id exists or not. */
export const CUSTOMER_SESSION_NOT_FOUND_CODE = 'CUSTOMER_SESSION_NOT_FOUND';

/** Problem codes after which this phone can do nothing more without a new QR from the shop. */
const SESSION_LOST_CODES: ReadonlySet<string> = new Set([
  CUSTOMER_QR_TOKEN_INVALID_CODE,
  CUSTOMER_SESSION_TOKEN_INVALID_CODE,
  CUSTOMER_SESSION_NOT_FOUND_CODE,
]);

export interface CustomerApiErrorDetails {
  retryAfterInSeconds?: number | undefined;
  hasProblemBody?: boolean | undefined;
  /** OTP_INCORRECT only: how many tries this OTP has left (ADR 0022 decision 3). */
  attemptsRemaining?: number | undefined;
}

// A failed customer API call as the screens see it: HTTP status, the stable problem code (mapped
// to translated text, never the English detail), Retry-After seconds, whether a problem+json body
// came, and the OTP tries left when the server sent them.
export class CustomerApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryAfterInSeconds: number | undefined;
  readonly hasProblemBody: boolean;
  readonly attemptsRemaining: number | undefined;

  // Keeps the status, the stable code and the optional details of one failed call.
  constructor(status: number, code: string, details: CustomerApiErrorDetails = {}) {
    super(`Customer API call failed with ${code} (${status})`);
    this.name = 'CustomerApiError';
    this.status = status;
    this.code = code;
    this.retryAfterInSeconds = details.retryAfterInSeconds;
    this.hasProblemBody = details.hasProblemBody ?? false;
    this.attemptsRemaining = details.attemptsRemaining;
  }
}

// Gives the problem code of any error a query or mutation raised; undefined for non-API errors.
export function readCustomerApiErrorCode(error: unknown): string | undefined {
  return error instanceof CustomerApiError ? error.code : undefined;
}

// True when the error means the phone has no usable session any more (a used QR, an expired or
// replaced token): the only way on is a new QR from the shop.
export function isSessionLostError(error: unknown): boolean {
  const code = readCustomerApiErrorCode(error);
  return code !== undefined && SESSION_LOST_CODES.has(code);
}

// True when the client cannot tell whether the server acted on a request: it never got an answer,
// a success came back unreadable, or a 5xx came without a problem body. Any problem+json answer
// is definite, whatever its status.
export function isRequestOutcomeUnknown(error: unknown): boolean {
  if (!(error instanceof CustomerApiError)) return true;
  if (error.code === NETWORK_UNAVAILABLE_CODE || error.code === UNEXPECTED_RESPONSE_CODE) {
    return true;
  }
  return error.status >= 500 && !error.hasProblemBody;
}
