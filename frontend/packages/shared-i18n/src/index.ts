// Public API of shared-i18n: i18next setup, language preference, money formatting and shared strings.
export {
  formatRupeesFromPaise,
  formatRupeesWithPaiseFromPaise,
  groupDigitsTheIndianWay,
} from './formatRupees';
export { initializeAppI18n, type InitializeAppI18nOptions } from './initializeAppI18n';
export {
  LANGUAGE_PREFERENCE_STORAGE_KEY,
  getDeviceStorage,
  readStoredLanguage,
  storeLanguage,
} from './languagePreferenceStorage';
export {
  SHARED_ENGLISH_TRANSLATIONS,
  SHARED_NAMESPACE,
  SHARED_TAMIL_TRANSLATIONS,
} from './sharedTranslations';
export {
  DEFAULT_LANGUAGE,
  SUPPORTED_LANGUAGES,
  isSupportedLanguage,
  type SupportedLanguage,
} from './supportedLanguages';
export {
  findMissingTranslationKeys,
  listTranslationKeys,
  type TranslationTree,
  type TranslationsMatching,
} from './translationTree';
export { useLanguagePreference, type LanguagePreference } from './useLanguagePreference';
