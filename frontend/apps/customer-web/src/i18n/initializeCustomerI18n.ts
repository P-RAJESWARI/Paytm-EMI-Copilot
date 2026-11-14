import { initializeAppI18n } from '@emi-copilot/shared-i18n';
import type { i18n } from 'i18next';

import {
  CUSTOMER_ENGLISH_TRANSLATIONS,
  CUSTOMER_NAMESPACE,
  CUSTOMER_TAMIL_TRANSLATIONS,
} from './customerTranslations';

// Builds the customer app's i18n instance: customer strings first, then the shared ones.
export function initializeCustomerI18n(): i18n {
  return initializeAppI18n({
    appNamespace: CUSTOMER_NAMESPACE,
    appTranslations: { en: CUSTOMER_ENGLISH_TRANSLATIONS, ta: CUSTOMER_TAMIL_TRANSLATIONS },
  });
}
