import type { SupportedLanguage } from '@emi-copilot/shared-i18n';

/** The shops are in Chennai and the backend reports in IST (plan Q21), so times show in IST. */
export const SHOP_TIME_ZONE = 'Asia/Kolkata';

const INTL_LOCALE_BY_LANGUAGE: Record<SupportedLanguage, string> = { en: 'en-IN', ta: 'ta-IN' };

// Gives the Intl locale for a supported app language.
export function toIntlLocale(language: SupportedLanguage): string {
  return INTL_LOCALE_BY_LANGUAGE[language];
}
