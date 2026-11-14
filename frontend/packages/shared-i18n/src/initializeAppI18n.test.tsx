import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { I18nextProvider } from 'react-i18next';
import { afterEach, describe, expect, it } from 'vitest';

import { initializeAppI18n } from './initializeAppI18n';
import { LANGUAGE_PREFERENCE_STORAGE_KEY } from './languagePreferenceStorage';
import { useLanguagePreference } from './useLanguagePreference';

const APP_TRANSLATIONS = {
  en: { screen: { title: 'Pair this device' } },
  ta: { screen: { title: 'இந்தச் சாதனத்தை இணைக்கவும்' } },
};

// Builds a fresh i18n instance for the test app.
function createTestI18n() {
  return initializeAppI18n({ appNamespace: 'testApp', appTranslations: APP_TRANSLATIONS });
}

afterEach(() => {
  window.localStorage.clear();
});

describe('initializeAppI18n', () => {
  it('starts in English with the app strings and falls back to the shared strings', () => {
    const i18n = createTestI18n();

    expect(i18n.language).toBe('en');
    expect(i18n.t('screen.title')).toBe('Pair this device');
    expect(i18n.t('saleStatus.READY_TO_PAY')).toBe('Ready to pay');
    expect(document.documentElement.lang).toBe('en');
  });

  it('starts in the language this device chose before', () => {
    window.localStorage.setItem(LANGUAGE_PREFERENCE_STORAGE_KEY, 'ta');

    const i18n = createTestI18n();

    expect(i18n.t('screen.title')).toBe('இந்தச் சாதனத்தை இணைக்கவும்');
    expect(i18n.t('saleStatus.PAID')).toBe('பணம் செலுத்தப்பட்டது');
    expect(document.documentElement.lang).toBe('ta');
  });

  it('remembers a language change on the device and on the page', async () => {
    const i18n = createTestI18n();

    await i18n.changeLanguage('ta');

    expect(window.localStorage.getItem(LANGUAGE_PREFERENCE_STORAGE_KEY)).toBe('ta');
    expect(document.documentElement.lang).toBe('ta');
  });

  it('falls back to and remembers English when asked for an unsupported language', async () => {
    const i18n = createTestI18n();

    await i18n.changeLanguage('fr');

    expect(i18n.t('screen.title')).toBe('Pair this device');
    expect(window.localStorage.getItem(LANGUAGE_PREFERENCE_STORAGE_KEY)).toBe('en');
  });

  it("does not store i18next's key-display mode as a language", async () => {
    const i18n = createTestI18n();

    await i18n.changeLanguage('cimode');

    expect(window.localStorage.getItem(LANGUAGE_PREFERENCE_STORAGE_KEY)).toBeNull();
  });
});

describe('useLanguagePreference', () => {
  it('gives the current language and switches it', () => {
    const i18n = createTestI18n();
    const wrapper = ({ children }: { children: ReactNode }) => (
      <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
    );
    const { result } = renderHook(() => useLanguagePreference(), { wrapper });

    expect(result.current.selectedLanguage).toBe('en');

    act(() => {
      result.current.selectLanguage('ta');
    });

    expect(result.current.selectedLanguage).toBe('ta');
  });

  it('reports English while i18next shows keys instead of a language', async () => {
    const i18n = createTestI18n();
    await i18n.changeLanguage('cimode');
    const wrapper = ({ children }: { children: ReactNode }) => (
      <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
    );

    const { result } = renderHook(() => useLanguagePreference(), { wrapper });

    expect(result.current.selectedLanguage).toBe('en');
  });
});
