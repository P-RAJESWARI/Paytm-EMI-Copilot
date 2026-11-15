import { createCorrelationIdMiddleware } from '@emi-copilot/api-client';
import createClient, { type Client } from 'openapi-fetch';

import type { CustomerApiPaths } from './customerContractTypes';
import { createCustomerSessionTokenMiddleware } from './customerSessionTokenMiddleware';

/** A typed openapi-fetch client for the customer endpoints. */
export type CustomerApiClient = Client<CustomerApiPaths>;

export interface CustomerApiClientOptions {
  baseUrl: string;
  /** Returns the session token held in memory, or undefined before the QR exchange. */
  getSessionToken: () => string | undefined;
  fetchFunction: (request: Request) => Promise<Response>;
}

// Pattern: Factory. Builds the customer client with the correlation-id and session-token
// middleware, so no screen ever sets those headers.
export function createCustomerApiClient({
  baseUrl,
  getSessionToken,
  fetchFunction,
}: CustomerApiClientOptions): CustomerApiClient {
  const apiClient = createClient<CustomerApiPaths>({ baseUrl, fetch: fetchFunction });
  apiClient.use(createCorrelationIdMiddleware());
  apiClient.use(createCustomerSessionTokenMiddleware(getSessionToken));
  return apiClient;
}
