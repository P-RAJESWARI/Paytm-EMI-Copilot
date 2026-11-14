import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

/** i18next namespace of the customer app's own strings; shared strings live in shared-i18n. */
export const CUSTOMER_NAMESPACE = 'customer';

// English customer strings; Layer 3 adds the C1 to C10 screens.
export const CUSTOMER_ENGLISH_TRANSLATIONS = {
  placeholder: {
    tagline: 'Buy on EMI knowing every cost',
  },
} as const;

// Tamil customer strings; the compiler checks they have exactly the English keys.
export const CUSTOMER_TAMIL_TRANSLATIONS: TranslationsMatching<
  typeof CUSTOMER_ENGLISH_TRANSLATIONS
> = {
  placeholder: {
    tagline: 'எல்லா செலவும் தெரிந்து EMI-யில் வாங்குங்கள்', // draft: needs native review
  },
};
