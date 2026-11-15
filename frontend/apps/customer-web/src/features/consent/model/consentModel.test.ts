import { describe, expect, it } from 'vitest';

import { CustomerApiError } from '../../customer-flow';
import { classifyConsentFailure } from './consentFailure';
import { formatCountdown } from './formatCountdown';

describe('classifyConsentFailure', () => {
  it.each([
    [
      new CustomerApiError(422, 'OTP_INCORRECT', { attemptsRemaining: 2 }),
      { kind: 'otpIncorrect', attemptsRemaining: 2 },
    ],
    [
      new CustomerApiError(422, 'OTP_INCORRECT'),
      { kind: 'otpIncorrect', attemptsRemaining: undefined },
    ],
    [new CustomerApiError(422, 'OTP_EXPIRED'), { kind: 'otpExpired' }],
    [new CustomerApiError(422, 'OTP_NOT_REQUESTED'), { kind: 'otpExpired' }],
    [new CustomerApiError(409, 'SHOWN_PLAN_CHANGED'), { kind: 'shownPlanChanged' }],
    [new CustomerApiError(409, 'CONSENT_ALREADY_GIVEN'), { kind: 'consentAlreadyGiven' }],
    [new CustomerApiError(429, 'RATE_LIMITED'), { kind: 'other' }],
    [new Error('anything else'), { kind: 'other' }],
  ])('sorts %o', (error, expectedFailure) => {
    expect(classifyConsentFailure(error)).toEqual(expectedFailure);
  });
});

describe('formatCountdown', () => {
  it.each([
    [24, '0:24'],
    [30, '0:30'],
    [65, '1:05'],
    [0, '0:00'],
    [-3, '0:00'],
    [4.2, '0:05'],
  ])('shows %d seconds as %s', (remainingSeconds, expectedText) => {
    expect(formatCountdown(remainingSeconds)).toBe(expectedText);
  });
});
