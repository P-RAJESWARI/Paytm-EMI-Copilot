import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import type { i18n } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { RouterProvider, type createBrowserRouter } from 'react-router';

import type { FetchFunction } from '../shared/api/merchantApiContext';
import { MerchantApiProvider } from '../shared/api/MerchantApiProvider';
import type { MerchantSession } from '../shared/session/merchantSessionContext';
import { MerchantSessionProvider } from '../shared/session/MerchantSessionProvider';

export interface AppProps {
  i18n: i18n;
  queryClient: QueryClient;
  /** A browser router in the app, a memory router in tests. */
  router: ReturnType<typeof createBrowserRouter>;
  /** Replaces the browser fetch; tests pass a fake backend. */
  fetchFunction?: FetchFunction | undefined;
  /** Starts already paired; only tests pass it, because the token lives in memory only. */
  initialSession?: MerchantSession | undefined;
}

// The merchant app root: translations, the server-data cache, the in-memory session, the API
// client and the router, in that order.
export function App({ i18n, queryClient, router, fetchFunction, initialSession }: AppProps) {
  return (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <MerchantSessionProvider initialSession={initialSession}>
          <MerchantApiProvider fetchFunction={fetchFunction}>
            <RouterProvider router={router} />
          </MerchantApiProvider>
        </MerchantSessionProvider>
      </QueryClientProvider>
    </I18nextProvider>
  );
}
