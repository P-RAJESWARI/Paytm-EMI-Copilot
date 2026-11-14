import i18next, { type i18n } from 'i18next';
import { initReactI18next } from 'react-i18next';

import { getDeviceStorage, readStoredLanguage, storeLanguage } from './languagePreferenceStorage';
import {
  SHARED_ENGLISH_TRANSLATIONS,
  SHARED_NAMESPACE,
  SHARED_TAMIL_TRANSLATIONS,
} from './sharedTranslations';
import {
  DEFAULT_LANGUAGE,
  SUPPORTED_LANGUAGES,
  isSupportedLanguage,
  type SupportedLanguage,
} from './supportedLanguages';
import type { TranslationTree } from './translationTree';

export interface InitializeAppI18nOptions {
  /** The app's own namespace, for example "merchant"; it becomes the default namespace. */
  appNamespace: string;
  appTranslations: Record<SupportedLanguage, TranslationTree>;
  /** Where the language choice is remembered; defaults to the device's localStorage. */
  storage?: Storage | undefined;
}

// Sets the page language so screen readers pronounce Tamil and English correctly.
function applyDocumentLanguage(language: SupportedLanguage): void {
  document.documentElement.lang = language;
}

// Pattern: Factory. Builds one ready-to-use i18next instance per app: the app's strings plus the
// shared ones (looked up when a key is not in the app namespace), starting in the language this
// device chose last time and remembering every later choice.
export function initializeAppI18n({
  appNamespace,
  appTranslations,
  storage = getDeviceStorage(),
}: InitializeAppI18nOptions): i18n {
  const instance = i18next.createInstance();
  const initialLanguage = readStoredLanguage(storage) ?? DEFAULT_LANGUAGE;
  // Resources are inline and initAsync is off, so init finishes before this function returns.
  void instance.use(initReactI18next).init({
    resources: {
      en: { [SHARED_NAMESPACE]: SHARED_ENGLISH_TRANSLATIONS, [appNamespace]: appTranslations.en },
      ta: { [SHARED_NAMESPACE]: SHARED_TAMIL_TRANSLATIONS, [appNamespace]: appTranslations.ta },
    },
    lng: initialLanguage,
    fallbackLng: DEFAULT_LANGUAGE,
    supportedLngs: SUPPORTED_LANGUAGES,
    ns: [appNamespace, SHARED_NAMESPACE],
    defaultNS: appNamespace,
    fallbackNS: SHARED_NAMESPACE,
    // React escapes rendered text already; escaping twice would show "&amp;".
    interpolation: { escapeValue: false },
    initAsync: false,
    returnNull: false,
  });
  applyDocumentLanguage(initialLanguage);
  instance.on('languageChanged', (language) => {
    if (!isSupportedLanguage(language)) return;
    storeLanguage(storage, language);
    applyDocumentLanguage(language);
  });
  return instance;
}
