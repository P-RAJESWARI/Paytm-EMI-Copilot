// Entry point of the customer app: styles, translations and the placeholder screen (Layer 3 fills it).
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { I18nextProvider } from 'react-i18next';

import './styles.css';
import { CustomerAppPlaceholder } from './app/CustomerAppPlaceholder';
import { initializeCustomerI18n } from './i18n/initializeCustomerI18n';

const rootElement = document.getElementById('root');
if (rootElement === null) throw new Error('index.html must contain an element with id "root"');

createRoot(rootElement).render(
  <StrictMode>
    <I18nextProvider i18n={initializeCustomerI18n()}>
      <CustomerAppPlaceholder />
    </I18nextProvider>
  </StrictMode>,
);
