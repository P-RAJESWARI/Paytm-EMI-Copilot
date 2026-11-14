import type { SupportedLanguage } from '@emi-copilot/shared-i18n';

import { toIntlLocale } from './shopLocale';

// Joins choices the way the language says "or", for example "9 or 12" or "₹2,444 or ₹1,833".
export function formatAlternatives(
  choices: readonly string[],
  language: SupportedLanguage,
): string {
  return new Intl.ListFormat(toIntlLocale(language), { type: 'disjunction' }).format(choices);
}
