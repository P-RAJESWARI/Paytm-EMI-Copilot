import { createBackendApiClient } from '@emi-copilot/api-client';
import { useState, type ReactNode } from 'react';

import { useMerchantSession } from '../session/useMerchantSession';
import { createSignOutOnAuthenticationLostMiddleware } from './createSignOutOnAuthenticationLostMiddleware';
import {
  MerchantApiContext,
  type FetchFunction,
  type MerchantApiContextValue,
} from './merchantApiContext';

export interface MerchantApiProviderProps {
  children: ReactNode;
  /** Replaces the browser fetch, for tests. */
  fetchFunction?: FetchFunction | undefined;
}

// Calls the browser's fetch with the window as `this`, which some browsers require.
function fetchWithBrowser(request: Request): Promise<Response> {
  return window.fetch(request);
}

// Builds the one generated API client for the app: it adds the in-memory token to every call
// and signs the tablet out when the server says the token is no longer valid.
export function MerchantApiProvider({
  children,
  fetchFunction = fetchWithBrowser,
}: MerchantApiProviderProps) {
  const { getAccessToken, signOut } = useMerchantSession();
  const [contextValue] = useState<MerchantApiContextValue>(() => {
    const baseUrl = window.location.origin;
    const apiClient = createBackendApiClient({ baseUrl, getAccessToken, fetch: fetchFunction });
    apiClient.use(createSignOutOnAuthenticationLostMiddleware(signOut));
    return { apiClient, fetchFunction, baseUrl };
  });
  return <MerchantApiContext.Provider value={contextValue}>{children}</MerchantApiContext.Provider>;
}
