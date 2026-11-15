import { readCustomerApiErrorCode } from '../api/customerApiError';

/** Problem codes with their own calm, translated message under `problems.<code>`. */
const CODES_WITH_OWN_MESSAGE: ReadonlySet<string> = new Set([
  'NETWORK_UNAVAILABLE',
  'RATE_LIMITED',
  'PAYMENT_GATEWAY_UNAVAILABLE',
  'PAYMENT_GATEWAY_TIMEOUT',
  'REQUEST_VALIDATION_FAILED',
]);

// Gives the translation key of the calm message for an error: its own when the code has one,
// otherwise the general "something did not load" text. The English detail is never shown.
export function getProblemMessageKey(error: unknown): string {
  const code = readCustomerApiErrorCode(error);
  return code !== undefined && CODES_WITH_OWN_MESSAGE.has(code)
    ? `problems.${code}`
    : 'problems.generic';
}
