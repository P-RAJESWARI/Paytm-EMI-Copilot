import { isSupportedLanguage, type SupportedLanguage } from './supportedLanguages';

/** Only the language choice is stored on the device; never tokens or personal data. */
export const LANGUAGE_PREFERENCE_STORAGE_KEY = 'emiCopilot.language';

// Gives the device's localStorage, or undefined where the browser blocks it (for example
// some private modes throw a SecurityError); the app then simply starts in the default language.
export function getDeviceStorage(): Storage | undefined {
  try {
    return window.localStorage;
  } catch (error) {
    if (error instanceof DOMException) return undefined;
    throw error;
  }
}

// Reads the language this device chose last time, ignoring anything unexpected.
export function readStoredLanguage(storage: Storage | undefined): SupportedLanguage | undefined {
  const storedValue = storage?.getItem(LANGUAGE_PREFERENCE_STORAGE_KEY);
  return isSupportedLanguage(storedValue) ? storedValue : undefined;
}

// Remembers the chosen language on this device.
export function storeLanguage(storage: Storage | undefined, language: SupportedLanguage): void {
  storage?.setItem(LANGUAGE_PREFERENCE_STORAGE_KEY, language);
}
