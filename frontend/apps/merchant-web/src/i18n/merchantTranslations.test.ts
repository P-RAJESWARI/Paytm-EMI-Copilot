import { findMissingTranslationKeys } from '@emi-copilot/shared-i18n';
import { describe, expect, it } from 'vitest';

import { findTamilLinesWithoutDraftMarker } from '@test-support/translationDrafts';

import { MERCHANT_ENGLISH_TRANSLATIONS, MERCHANT_TAMIL_TRANSLATIONS } from './merchantTranslations';

/** The source of every per-area translation file, so each one's Tamil lines are checked. */
const TRANSLATION_SOURCES_BY_FILE = import.meta.glob<string>('./*Translations.ts', {
  query: '?raw',
  import: 'default',
  eager: true,
});

// Lists the names of the exported Tamil translation objects in one file's source.
function findTamilObjectNames(source: string): string[] {
  return [...source.matchAll(/export const (\w+_TAMIL_TRANSLATIONS)/g)].map(
    (match) => match[1] ?? '',
  );
}

describe('merchant translations', () => {
  it('has a Tamil string for every English key and no extra Tamil keys', () => {
    expect(
      findMissingTranslationKeys(MERCHANT_ENGLISH_TRANSLATIONS, MERCHANT_TAMIL_TRANSLATIONS),
    ).toEqual([]);
    expect(
      findMissingTranslationKeys(MERCHANT_TAMIL_TRANSLATIONS, MERCHANT_ENGLISH_TRANSLATIONS),
    ).toEqual([]);
  });

  it('reads every per-area translation file', () => {
    expect(Object.keys(TRANSLATION_SOURCES_BY_FILE).length).toBeGreaterThanOrEqual(3);
  });

  it.each(Object.entries(TRANSLATION_SOURCES_BY_FILE))(
    'marks every Tamil string in %s as a draft that needs native review',
    (_fileName, source) => {
      for (const tamilObjectName of findTamilObjectNames(source)) {
        expect(findTamilLinesWithoutDraftMarker(source, tamilObjectName)).toEqual([]);
      }
    },
  );
});
