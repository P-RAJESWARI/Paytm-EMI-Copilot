import { QueryClient } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import type { ReactNode } from 'react';

import { CustomerApp } from '../app/CustomerApp';
import {
  FixtureCustomerFlowApi,
  type CustomerFlowApi,
  type CustomerFlowState,
} from '../features/customer-flow';
import { initializeCustomerI18n } from '../i18n/initializeCustomerI18n';

/** The QR token tests open the app with. */
export const TEST_QR_TOKEN = 'test-qr-token-4821';

export interface RenderCustomerAppOptions {
  children: ReactNode;
  /** Defaults to a fresh fixture with the design sample. */
  customerFlowApi?: CustomerFlowApi | undefined;
  /** Defaults to TEST_QR_TOKEN; pass null to open the page without a token. */
  qrToken?: string | null | undefined;
  initialFlowState?: CustomerFlowState | undefined;
}

// Builds a query cache without retries, so loading and error states show at once.
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { retry: false } },
  });
}

// Renders the customer app with fresh translations, cache and (by default) the fixture API.
export function renderCustomerApp({
  children,
  customerFlowApi = new FixtureCustomerFlowApi(),
  qrToken,
  initialFlowState,
}: RenderCustomerAppOptions) {
  const queryClient = createTestQueryClient();
  const renderResult = render(
    <CustomerApp
      i18n={initializeCustomerI18n()}
      queryClient={queryClient}
      customerFlowApi={customerFlowApi}
      qrToken={qrToken === null ? undefined : (qrToken ?? TEST_QR_TOKEN)}
      initialFlowState={initialFlowState}
    >
      {children}
    </CustomerApp>,
  );
  return { ...renderResult, customerFlowApi, queryClient };
}
