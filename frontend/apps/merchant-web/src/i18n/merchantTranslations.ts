import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

import {
  COUNTER_SALE_ENGLISH_TRANSLATIONS,
  COUNTER_SALE_TAMIL_TRANSLATIONS,
} from './counterSaleTranslations';
import {
  PAYMENT_HANDOFF_ENGLISH_TRANSLATIONS,
  PAYMENT_HANDOFF_TAMIL_TRANSLATIONS,
} from './paymentHandoffTranslations';
import { PAIRING_ENGLISH_TRANSLATIONS, PAIRING_TAMIL_TRANSLATIONS } from './pairingTranslations';
import { PROBLEM_ENGLISH_TRANSLATIONS, PROBLEM_TAMIL_TRANSLATIONS } from './problemTranslations';
import {
  SALES_REPORT_ENGLISH_TRANSLATIONS,
  SALES_REPORT_TAMIL_TRANSLATIONS,
} from './salesReportTranslations';
import { SHELL_ENGLISH_TRANSLATIONS, SHELL_TAMIL_TRANSLATIONS } from './shellTranslations';
import {
  WEEKLY_MESSAGE_ENGLISH_TRANSLATIONS,
  WEEKLY_MESSAGE_TAMIL_TRANSLATIONS,
} from './weeklyMessageTranslations';

/** i18next namespace of the merchant app's own strings; shared strings live in shared-i18n. */
export const MERCHANT_NAMESPACE = 'merchant';

// English merchant strings, composed from one file per screen area so each stays readable.
export const MERCHANT_ENGLISH_TRANSLATIONS = {
  ...SHELL_ENGLISH_TRANSLATIONS,
  ...PAIRING_ENGLISH_TRANSLATIONS,
  ...PROBLEM_ENGLISH_TRANSLATIONS,
  ...COUNTER_SALE_ENGLISH_TRANSLATIONS,
  ...PAYMENT_HANDOFF_ENGLISH_TRANSLATIONS,
  ...SALES_REPORT_ENGLISH_TRANSLATIONS,
  ...WEEKLY_MESSAGE_ENGLISH_TRANSLATIONS,
} as const;

// Tamil merchant strings, composed the same way; the compiler checks they have exactly the English keys.
export const MERCHANT_TAMIL_TRANSLATIONS: TranslationsMatching<
  typeof MERCHANT_ENGLISH_TRANSLATIONS
> = {
  ...SHELL_TAMIL_TRANSLATIONS,
  ...PAIRING_TAMIL_TRANSLATIONS,
  ...PROBLEM_TAMIL_TRANSLATIONS,
  ...COUNTER_SALE_TAMIL_TRANSLATIONS,
  ...PAYMENT_HANDOFF_TAMIL_TRANSLATIONS,
  ...SALES_REPORT_TAMIL_TRANSLATIONS,
  ...WEEKLY_MESSAGE_TAMIL_TRANSLATIONS,
};
