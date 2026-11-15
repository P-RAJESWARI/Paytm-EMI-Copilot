import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import type { i18n } from 'i18next';
import type { ReactNode } from 'react';
import { I18nextProvider } from 'react-i18next';

import {
  CustomerFlowApiContext,
  CustomerSessionGate,
  type CustomerFlowApi,
  type CustomerFlowState,
} from '../features/customer-flow';

export interface CustomerAppProps {
  i18n: i18n;
  queryClient: QueryClient;
  /** The fixture or HTTP implementation the factory chose; tests pass their own. */
  customerFlowApi: CustomerFlowApi;
  /** The QR token from the URL fragment, held in memory only. */
  qrToken: string | undefined;
  /** The flow's screens. */
  children: ReactNode;
  /** Starts the flow at another step; only tests pass it. */
  initialFlowState?: CustomerFlowState | undefined;
}

// The customer app root: translations, the server-data cache, the customer API, then the session
// gate that opens the QR's session before any screen of the flow shows.
export function CustomerApp({
  i18n,
  queryClient,
  customerFlowApi,
  qrToken,
  children,
  initialFlowState,
}: CustomerAppProps) {
  return (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <CustomerFlowApiContext.Provider value={customerFlowApi}>
          <CustomerSessionGate qrToken={qrToken} initialFlowState={initialFlowState}>
            {children}
          </CustomerSessionGate>
        </CustomerFlowApiContext.Provider>
      </QueryClientProvider>
    </I18nextProvider>
  );
}
