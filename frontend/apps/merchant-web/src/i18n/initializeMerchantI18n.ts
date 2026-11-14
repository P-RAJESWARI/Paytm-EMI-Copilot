import { initializeAppI18n } from '@emi-copilot/shared-i18n';
import type { i18n } from 'i18next';

import {
  MERCHANT_ENGLISH_TRANSLATIONS,
  MERCHANT_NAMESPACE,
  MERCHANT_TAMIL_TRANSLATIONS,
} from './merchantTranslations';

// Builds the merchant app's i18n instance: merchant strings first, then the shared ones.
export function initializeMerchantI18n(): i18n {
  return initializeAppI18n({
    appNamespace: MERCHANT_NAMESPACE,
    appTranslations: { en: MERCHANT_ENGLISH_TRANSLATIONS, ta: MERCHANT_TAMIL_TRANSLATIONS },
  });
}
