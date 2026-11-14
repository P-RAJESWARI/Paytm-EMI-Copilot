import { describe, expect, it } from 'vitest';

import { readProblemCode } from './problemDetails';

describe('readProblemCode', () => {
  it('reads the stable code of a problem body', () => {
    expect(readProblemCode({ status: 401, code: 'MERCHANT_AUTHENTICATION_REQUIRED' })).toBe(
      'MERCHANT_AUTHENTICATION_REQUIRED',
    );
  });

  it.each([
    ['undefined', undefined],
    ['null', null],
    ['a string', 'Bad gateway'],
    ['an object without a code', { status: 500 }],
    ['a non-string code', { code: 42 }],
  ])('gives undefined for %s', (_description, errorBody) => {
    expect(readProblemCode(errorBody)).toBeUndefined();
  });
});
