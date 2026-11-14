import { describe, expect, it } from 'vitest';

import { findMissingTranslationKeys, listTranslationKeys } from './translationTree';

describe('listTranslationKeys', () => {
  it('lists nested leaves as dotted paths', () => {
    expect(listTranslationKeys({ a: 'A', b: { c: 'C', d: { e: 'E' } } })).toEqual([
      'a',
      'b.c',
      'b.d.e',
    ]);
  });
});

describe('findMissingTranslationKeys', () => {
  it('reports keys that are missing, empty or not a string in the candidate', () => {
    const englishTree = { title: 'Title', body: 'Body', footer: { note: 'Note' }, label: 'Label' };
    const tamilTree = { title: 'தலைப்பு', body: '  ', footer: 'not a tree' };

    expect(findMissingTranslationKeys(englishTree, tamilTree)).toEqual([
      'body',
      'footer.note',
      'label',
    ]);
  });

  it('reports nothing when every key has text', () => {
    expect(findMissingTranslationKeys({ a: { b: 'B' } }, { a: { b: 'பி' } })).toEqual([]);
  });
});
