import { readMerchantApiErrorCode } from './merchantApiError';

/** Problem codes with their own calm, translated message under `problems.<code>`. */
const CODES_WITH_OWN_MESSAGE = new Set([
  'NETWORK_UNAVAILABLE',
  'RATE_LIMITED',
  'SALE_NOT_FOUND',
  'PRODUCT_NOT_FOUND',
  'SALE_STATE_CONFLICT',
  'SESSION_CODES_EXHAUSTED',
  'CHOSEN_PLAN_NO_LONGER_OFFERED',
  'PAYMENT_LINK_ALREADY_ACTIVE',
  'PAYMENT_LINK_CREATION_IN_PROGRESS',
  'PAYMENT_LINK_OUTCOME_UNKNOWN',
  'PAYMENT_LINK_CREATION_FAILED',
  'PAYMENT_GATEWAY_TIMEOUT',
  'PAYMENT_GATEWAY_UNAVAILABLE',
  'PAYMENT_GATEWAY_REQUEST_REJECTED',
  'PAYMENT_GATEWAY_ERROR',
  'MERCHANT_AUTHENTICATION_REQUIRED',
]);

// Gives the translation key of the calm message for an error: its own when the code has one,
// otherwise the general "something did not load" text. The English detail is never shown.
export function getProblemMessageKey(error: unknown): string {
  const code = readMerchantApiErrorCode(error);
  return code !== undefined && CODES_WITH_OWN_MESSAGE.has(code)
    ? `problems.${code}`
    : 'problems.generic';
}
