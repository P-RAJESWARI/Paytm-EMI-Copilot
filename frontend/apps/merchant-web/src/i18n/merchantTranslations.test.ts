import { findMissingTranslationKeys } from '@emi-copilot/shared-i18n';
import { describe, expect, it } from 'vitest';

import { findTamilLinesWithoutDraftMarker } from '@test-support/translationDrafts';

import { MERCHANT_ENGLISH_TRANSLATIONS, MERCHANT_TAMIL_TRANSLATIONS } from './merchantTranslations';
import merchantTranslationsSource from './merchantTranslations.ts?raw';

describe('merchant translations', () => {
  it('has a Tamil string for every English key and no extra Tamil keys', () => {
    expect(
      findMissingTranslationKeys(MERCHANT_ENGLISH_TRANSLATIONS, MERCHANT_TAMIL_TRANSLATIONS),
    ).toEqual([]);
    expect(
      findMissingTranslationKeys(MERCHANT_TAMIL_TRANSLATIONS, MERCHANT_ENGLISH_TRANSLATIONS),
    ).toEqual([]);
  });

  it('marks every Tamil string as a draft that needs native review', () => {
    expect(
      findTamilLinesWithoutDraftMarker(merchantTranslationsSource, 'MERCHANT_TAMIL_TRANSLATIONS'),
    ).toEqual([]);
  });
});
