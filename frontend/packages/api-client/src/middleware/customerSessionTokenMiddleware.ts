import type { Middleware } from 'openapi-fetch';

/** The header every customer call after the QR exchange carries (api-conventions.md section 5). */
export const CUSTOMER_SESSION_TOKEN_HEADER = 'X-Customer-Session-Token';

// Adds X-Customer-Session-Token when the phone holds a session token. The token is read through
// the getter on every request and never kept, logged or stored by this package.
export function createCustomerSessionTokenMiddleware(
  getSessionToken: () => string | undefined,
): Middleware {
  return {
    // Sets the header on the outgoing request unless the caller already did.
    onRequest({ request }) {
      const sessionToken = getSessionToken();
      if (
        sessionToken !== undefined &&
        sessionToken !== '' &&
        !request.headers.has(CUSTOMER_SESSION_TOKEN_HEADER)
      ) {
        request.headers.set(CUSTOMER_SESSION_TOKEN_HEADER, sessionToken);
      }
      return request;
    },
  };
}
