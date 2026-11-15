import createClient, { type Client } from 'openapi-fetch';

import type { paths } from './generated/backendApiSchema';
import { createAuthorizationMiddleware } from './middleware/authorizationMiddleware';
import { createCorrelationIdMiddleware } from './middleware/correlationIdMiddleware';
import { createCustomerSessionTokenMiddleware } from './middleware/customerSessionTokenMiddleware';

/** A typed client for every /api/v1 endpoint in backend/openapi.json. */
export type BackendApiClient = Client<paths>;

export interface BackendApiClientOptions {
  /** API origin; defaults to the page's own origin, which the Vite dev proxy forwards to FastAPI. */
  baseUrl?: string | undefined;
  /** Returns the merchant token the app holds in memory, or undefined before pairing. */
  getAccessToken?: (() => string | undefined) | undefined;
  /** Returns the customer session token held in memory, or undefined before the QR exchange. */
  getCustomerSessionToken?: (() => string | undefined) | undefined;
  /** Makes a fresh correlation id per request; defaults to a random UUID v4. */
  createCorrelationId?: (() => string) | undefined;
  /** Replaces the global fetch, for tests. */
  fetch?: ((request: Request) => Promise<Response>) | undefined;
}

// Pattern: Factory. Builds the generated openapi-fetch client with the correlation-id and
// (when a token getter is given) authorization or customer session-token middleware, so features
// never set these headers.
export function createBackendApiClient({
  baseUrl = window.location.origin,
  getAccessToken,
  getCustomerSessionToken,
  createCorrelationId,
  fetch,
}: BackendApiClientOptions = {}): BackendApiClient {
  const client = createClient<paths>(fetch === undefined ? { baseUrl } : { baseUrl, fetch });
  client.use(createCorrelationIdMiddleware(createCorrelationId));
  if (getAccessToken !== undefined) {
    client.use(createAuthorizationMiddleware(getAccessToken));
  }
  if (getCustomerSessionToken !== undefined) {
    client.use(createCustomerSessionTokenMiddleware(getCustomerSessionToken));
  }
  return client;
}
