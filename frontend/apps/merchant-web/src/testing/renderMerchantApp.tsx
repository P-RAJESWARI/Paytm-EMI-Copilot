import { QueryClient } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { createMemoryRouter } from 'react-router';

import { App } from '../app/App';
import { MERCHANT_ROUTES } from '../app/merchantRoutes';
import { initializeMerchantI18n } from '../i18n/initializeMerchantI18n';
import type { MerchantSession } from '../shared/session/merchantSessionContext';
import {
  createFakeMerchantBackend,
  type FakeMerchantBackend,
  type FakeRoutes,
} from './fakeMerchantBackend';
import { TEST_MERCHANT_SESSION } from './merchantTestData';

export interface RenderMerchantAppOptions {
  path: string;
  routes?: FakeRoutes | undefined;
  /** Defaults to the paired demo shop; pass null to start unpaired. */
  session?: MerchantSession | null | undefined;
}

// Builds a query cache without retries or caching between tests, so states show at once.
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { retry: false } },
  });
}

// Renders the whole merchant app at a path against a fake backend; gives the backend, the
// router and the query cache so tests can drive and inspect them.
export function renderMerchantApp({ path, routes = {}, session }: RenderMerchantAppOptions) {
  const fakeBackend: FakeMerchantBackend = createFakeMerchantBackend({
    'GET /api/v1/merchants/me': () =>
      new Response(JSON.stringify(TEST_MERCHANT_SESSION.merchant), {
        headers: { 'Content-Type': 'application/json' },
      }),
    'GET /api/v1/sales/events': () =>
      new Response(new ReadableStream(), {
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    ...routes,
  });
  const router = createMemoryRouter(MERCHANT_ROUTES, { initialEntries: [path] });
  const queryClient = createTestQueryClient();
  const renderResult = render(
    <App
      i18n={initializeMerchantI18n()}
      queryClient={queryClient}
      router={router}
      fetchFunction={fakeBackend.fetchFunction}
      initialSession={session === null ? undefined : (session ?? TEST_MERCHANT_SESSION)}
    />,
  );
  return { ...renderResult, fakeBackend, router, queryClient };
}
