import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

import {
  DEFAULT_LANGUAGE,
  isSupportedLanguage,
  type SupportedLanguage,
} from './supportedLanguages';

export interface LanguagePreference {
  selectedLanguage: SupportedLanguage;
  selectLanguage: (language: SupportedLanguage) => void;
}

// Gives the current language and a way to switch it, ready to wire into the ui-kit LanguageToggle.
export function useLanguagePreference(): LanguagePreference {
  const { i18n } = useTranslation();
  const selectedLanguage = isSupportedLanguage(i18n.resolvedLanguage)
    ? i18n.resolvedLanguage
    : DEFAULT_LANGUAGE;
  const selectLanguage = useCallback(
    (language: SupportedLanguage) => {
      // Inline resources make the switch synchronous; the promise carries nothing to wait for.
      void i18n.changeLanguage(language);
    },
    [i18n],
  );
  return { selectedLanguage, selectLanguage };
}
