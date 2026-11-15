// Entry point of the customer app: takes the QR token from the URL fragment (then removes it),
// picks the CustomerFlowApi, and renders the flow inside its providers.
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import './styles.css';
import { CustomerApp } from './app/CustomerApp';
import { CustomerFlowScreens } from './app/CustomerFlowScreens';
import { createCustomerQueryClient } from './app/createCustomerQueryClient';
import { takeQrTokenFromLocation } from './app/takeQrTokenFromLocation';
import {
  createCustomerFlowApi,
  readCustomerFlowApiMode,
  type CustomerFlowApi,
} from './features/customer-flow';
import { initializeCustomerI18n } from './i18n/initializeCustomerI18n';

const rootElement = document.getElementById('root');
if (rootElement === null) throw new Error('index.html must contain an element with id "root"');

const qrToken = takeQrTokenFromLocation(window);

// Renders the flow once the CustomerFlowApi is ready (the fixture loads lazily, see the factory).
function renderCustomerApp(container: HTMLElement, customerFlowApi: CustomerFlowApi): void {
  createRoot(container).render(
    <StrictMode>
      <CustomerApp
        i18n={initializeCustomerI18n()}
        queryClient={createCustomerQueryClient()}
        customerFlowApi={customerFlowApi}
        qrToken={qrToken}
      >
        <CustomerFlowScreens />
      </CustomerApp>
    </StrictMode>,
  );
}

void createCustomerFlowApi({
  mode: readCustomerFlowApiMode(import.meta.env.VITE_CUSTOMER_FLOW_API),
  baseUrl: window.location.origin,
  fetchFunction: (request) => window.fetch(request),
}).then((customerFlowApi) => {
  renderCustomerApp(rootElement, customerFlowApi);
});
