import { describe, expect, it } from 'vitest';

import { findTamilLinesWithoutDraftMarker } from '@test-support/translationDrafts';

import { SHARED_ENGLISH_TRANSLATIONS, SHARED_TAMIL_TRANSLATIONS } from './sharedTranslations';
import sharedTranslationsSource from './sharedTranslations.ts?raw';
import { findMissingTranslationKeys } from './translationTree';

const API_SALE_STATUSES = ['CHOOSING', 'READY_TO_PAY', 'PAID', 'PAYMENT_NOT_COMPLETED', 'EXPIRED'];

describe('shared translations', () => {
  it('has a Tamil string for every English key and no extra Tamil keys', () => {
    expect(
      findMissingTranslationKeys(SHARED_ENGLISH_TRANSLATIONS, SHARED_TAMIL_TRANSLATIONS),
    ).toEqual([]);
    expect(
      findMissingTranslationKeys(SHARED_TAMIL_TRANSLATIONS, SHARED_ENGLISH_TRANSLATIONS),
    ).toEqual([]);
  });

  it('marks every Tamil string as a draft that needs native review', () => {
    expect(
      findTamilLinesWithoutDraftMarker(sharedTranslationsSource, 'SHARED_TAMIL_TRANSLATIONS'),
    ).toEqual([]);
  });

  it('the draft check reports unmarked Tamil lines, including wrapped values', () => {
    const exampleSource = [
      'export const EXAMPLE_TAMIL = {',
      "  marked: 'குறி', // draft: needs native review",
      "  unmarked: 'குறியில்லை',",
      '  wrapped:',
      "    'நீண்ட உரை',",
      '};',
    ].join('\n');

    expect(findTamilLinesWithoutDraftMarker(exampleSource, 'EXAMPLE_TAMIL')).toEqual([
      "  unmarked: 'குறியில்லை',",
      "    'நீண்ட உரை',",
    ]);
  });

  it('labels every merchant-visible sale status from the API', () => {
    expect(Object.keys(SHARED_ENGLISH_TRANSLATIONS.saleStatus)).toEqual(API_SALE_STATUSES);
  });

  it('uses the agreed English status words', () => {
    expect(SHARED_ENGLISH_TRANSLATIONS.saleStatus).toEqual({
      CHOOSING: 'Choosing',
      READY_TO_PAY: 'Ready to pay',
      PAID: 'Paid',
      PAYMENT_NOT_COMPLETED: 'Payment not completed',
      EXPIRED: 'Expired',
    });
  });

  it('names exactly the three comfort bands from the API, in the agreed words', () => {
    expect(SHARED_ENGLISH_TRANSLATIONS.comfortBand).toEqual({
      COMFORTABLE: 'Comfortable',
      STRETCHING: 'Stretching',
      RISKY: 'Risky',
    });
  });

  it('never uses credit-decision words', () => {
    const allEnglishText = JSON.stringify(SHARED_ENGLISH_TRANSLATIONS).toLowerCase();

    expect(allEnglishText).not.toMatch(/declin|approv|reject|eligible/);
  });
});
