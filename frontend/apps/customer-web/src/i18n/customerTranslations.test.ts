import {
  findMissingTranslationKeys,
  listTranslationKeys,
  SHARED_ENGLISH_TRANSLATIONS,
} from '@emi-copilot/shared-i18n';
import { describe, expect, it } from 'vitest';

import { findTamilLinesWithoutDraftMarker } from '@test-support/translationDrafts';

import { CUSTOMER_ENGLISH_TRANSLATIONS, CUSTOMER_TAMIL_TRANSLATIONS } from './customerTranslations';

/** The source of every per-area translation file, so each one's Tamil lines are checked. */
const TRANSLATION_SOURCES_BY_FILE = import.meta.glob<string>('./*Translations.ts', {
  query: '?raw',
  import: 'default',
  eager: true,
});

/**
 * Wording customer screens must never use (CLAUDE.md rules 5 and 7, security-and-compliance.md
 * section 6): credit-decision words, "interest rate", "best for you" and urgency.
 */
const BANNED_CUSTOMER_WORDING =
  /approv|declin|reject|eligib|interest rate|best for you|recommended|hurry|act now|limited time|only today|last chance|expires soon|don't miss/i;

// Lists the names of the exported Tamil translation objects in one file's source.
function findTamilObjectNames(source: string): string[] {
  return [...source.matchAll(/export const (\w+_TAMIL_TRANSLATIONS)/g)].map(
    (match) => match[1] ?? '',
  );
}

describe('customer translations', () => {
  it('has a Tamil string for every English key and no extra Tamil keys', () => {
    expect(
      findMissingTranslationKeys(CUSTOMER_ENGLISH_TRANSLATIONS, CUSTOMER_TAMIL_TRANSLATIONS),
    ).toEqual([]);
    expect(
      findMissingTranslationKeys(CUSTOMER_TAMIL_TRANSLATIONS, CUSTOMER_ENGLISH_TRANSLATIONS),
    ).toEqual([]);
  });

  it.each(Object.entries(TRANSLATION_SOURCES_BY_FILE))(
    'marks every Tamil string in %s as a draft that needs native review',
    (_fileName, source) => {
      for (const tamilObjectName of findTamilObjectNames(source)) {
        expect(findTamilLinesWithoutDraftMarker(source, tamilObjectName)).toEqual([]);
      }
    },
  );

  it('never uses credit-decision, "interest rate", "best for you" or urgency wording', () => {
    const englishTexts = [
      JSON.stringify(CUSTOMER_ENGLISH_TRANSLATIONS),
      JSON.stringify(SHARED_ENGLISH_TRANSLATIONS),
    ];

    for (const englishText of englishTexts) {
      expect(englishText).not.toMatch(BANNED_CUSTOMER_WORDING);
    }
  });

  it('the wording check catches the banned phrases', () => {
    for (const bannedPhrase of [
      'Approved',
      'Your loan was declined',
      'Best for you',
      'Interest rate 14%',
      'Hurry',
    ]) {
      expect(bannedPhrase).toMatch(BANNED_CUSTOMER_WORDING);
    }
  });

  it('keeps keys semantic, never whole sentences', () => {
    const keys = listTranslationKeys(CUSTOMER_ENGLISH_TRANSLATIONS);

    expect(keys.filter((key) => /\s/.test(key))).toEqual([]);
  });
});
