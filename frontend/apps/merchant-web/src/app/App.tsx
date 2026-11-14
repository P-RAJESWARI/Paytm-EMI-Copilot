import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import type { i18n } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { RouterProvider, type createBrowserRouter } from 'react-router';

export interface AppProps {
  i18n: i18n;
  queryClient: QueryClient;
  /** A browser router in the app, a memory router in tests. */
  router: ReturnType<typeof createBrowserRouter>;
}

// The merchant app root: translations, the server-data cache and the router, in that order.
export function App({ i18n, queryClient, router }: AppProps) {
  return (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </I18nextProvider>
  );
}
