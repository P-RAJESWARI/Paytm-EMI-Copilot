import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  LANGUAGE_PREFERENCE_STORAGE_KEY,
  getDeviceStorage,
  readStoredLanguage,
  storeLanguage,
} from './languagePreferenceStorage';

afterEach(() => {
  // Restore first: some tests replace the localStorage getter with one that throws.
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe('language preference storage', () => {
  it('stores and reads back the chosen language', () => {
    storeLanguage(window.localStorage, 'ta');

    expect(window.localStorage.getItem(LANGUAGE_PREFERENCE_STORAGE_KEY)).toBe('ta');
    expect(readStoredLanguage(window.localStorage)).toBe('ta');
  });

  it('ignores a stored value that is not a supported language', () => {
    window.localStorage.setItem(LANGUAGE_PREFERENCE_STORAGE_KEY, 'fr');

    expect(readStoredLanguage(window.localStorage)).toBeUndefined();
  });

  it('does nothing without storage', () => {
    storeLanguage(undefined, 'ta');

    expect(readStoredLanguage(undefined)).toBeUndefined();
  });

  it('gives the device localStorage when the browser allows it', () => {
    expect(getDeviceStorage()).toBe(window.localStorage);
  });

  it('gives no storage when the browser blocks it with a SecurityError', () => {
    vi.spyOn(window, 'localStorage', 'get').mockImplementation(() => {
      throw new DOMException('Storage is blocked', 'SecurityError');
    });

    expect(getDeviceStorage()).toBeUndefined();
  });

  it('does not hide unexpected errors', () => {
    vi.spyOn(window, 'localStorage', 'get').mockImplementation(() => {
      throw new TypeError('unexpected');
    });

    expect(() => getDeviceStorage()).toThrow(TypeError);
  });
});
