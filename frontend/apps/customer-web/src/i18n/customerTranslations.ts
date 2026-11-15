import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

import { BUDGET_ENGLISH_TRANSLATIONS, BUDGET_TAMIL_TRANSLATIONS } from './budgetTranslations';
import { COMFORT_ENGLISH_TRANSLATIONS, COMFORT_TAMIL_TRANSLATIONS } from './comfortTranslations';
import { FLOW_ENGLISH_TRANSLATIONS, FLOW_TAMIL_TRANSLATIONS } from './flowTranslations';
import { PLAN_ENGLISH_TRANSLATIONS, PLAN_TAMIL_TRANSLATIONS } from './planTranslations';
import { WELCOME_ENGLISH_TRANSLATIONS, WELCOME_TAMIL_TRANSLATIONS } from './welcomeTranslations';

/** i18next namespace of the customer app's own strings; shared strings live in shared-i18n. */
export const CUSTOMER_NAMESPACE = 'customer';

// English customer strings, composed from one file per screen area so each stays readable.
export const CUSTOMER_ENGLISH_TRANSLATIONS = {
  ...FLOW_ENGLISH_TRANSLATIONS,
  ...WELCOME_ENGLISH_TRANSLATIONS,
  ...BUDGET_ENGLISH_TRANSLATIONS,
  ...COMFORT_ENGLISH_TRANSLATIONS,
  ...PLAN_ENGLISH_TRANSLATIONS,
} as const;

// Tamil customer strings, composed the same way; the compiler checks they have exactly the English keys.
export const CUSTOMER_TAMIL_TRANSLATIONS: TranslationsMatching<
  typeof CUSTOMER_ENGLISH_TRANSLATIONS
> = {
  ...FLOW_TAMIL_TRANSLATIONS,
  ...WELCOME_TAMIL_TRANSLATIONS,
  ...BUDGET_TAMIL_TRANSLATIONS,
  ...COMFORT_TAMIL_TRANSLATIONS,
  ...PLAN_TAMIL_TRANSLATIONS,
};
