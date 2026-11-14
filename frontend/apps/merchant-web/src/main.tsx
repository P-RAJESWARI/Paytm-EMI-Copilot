// Entry point of the merchant app: styles, translations, the query cache and the router.
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter } from 'react-router';

import './styles.css';
import { App } from './app/App';
import { createMerchantQueryClient } from './app/createMerchantQueryClient';
import { MERCHANT_ROUTES } from './app/merchantRoutes';
import { initializeMerchantI18n } from './i18n/initializeMerchantI18n';

const rootElement = document.getElementById('root');
if (rootElement === null) throw new Error('index.html must contain an element with id "root"');

createRoot(rootElement).render(
  <StrictMode>
    <App
      i18n={initializeMerchantI18n()}
      queryClient={createMerchantQueryClient()}
      router={createBrowserRouter(MERCHANT_ROUTES)}
    />
  </StrictMode>,
);
