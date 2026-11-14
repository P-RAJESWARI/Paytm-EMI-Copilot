// The two languages every customer-facing and merchant string exists in.
export const SUPPORTED_LANGUAGES = ['en', 'ta'] as const;

export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

export const DEFAULT_LANGUAGE: SupportedLanguage = 'en';

// Narrows any string (for example a stored value) to a supported language.
export function isSupportedLanguage(value: unknown): value is SupportedLanguage {
  return SUPPORTED_LANGUAGES.some((language) => language === value);
}
