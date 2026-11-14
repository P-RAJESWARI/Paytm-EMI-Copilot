import type { SupportedLanguage } from '@emi-copilot/shared-i18n';

import { toIntlLocale } from './shopLocale';

/** `dayAndMonth` gives "13 Jan"; `full` gives "13 Jan 2027". */
export type CalendarDateStyle = 'dayAndMonth' | 'full';

// Formats an API calendar date ("2027-01-13", no time) without shifting it by a time zone.
export function formatCalendarDate(
  calendarDate: string,
  language: SupportedLanguage,
  style: CalendarDateStyle,
): string {
  return new Intl.DateTimeFormat(toIntlLocale(language), {
    day: 'numeric',
    month: 'short',
    ...(style === 'full' ? { year: 'numeric' } : {}),
    timeZone: 'UTC',
  }).format(new Date(`${calendarDate}T00:00:00Z`));
}
