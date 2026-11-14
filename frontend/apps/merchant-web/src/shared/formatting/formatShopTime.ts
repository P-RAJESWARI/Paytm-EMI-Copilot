import type { SupportedLanguage } from '@emi-copilot/shared-i18n';

import { SHOP_TIME_ZONE, toIntlLocale } from './shopLocale';

// Gives the shop's clock time of a UTC timestamp, for example "3:40 pm" for "Paid at 3:40 pm".
export function formatShopTime(isoDateTime: string, language: SupportedLanguage): string {
  return new Intl.DateTimeFormat(toIntlLocale(language), {
    hour: 'numeric',
    minute: '2-digit',
    timeZone: SHOP_TIME_ZONE,
  }).format(new Date(isoDateTime));
}
