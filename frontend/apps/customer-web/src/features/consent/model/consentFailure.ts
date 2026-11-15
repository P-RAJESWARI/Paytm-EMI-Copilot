import { CustomerApiError, readCustomerApiErrorCode } from '../../customer-flow';

/** What a refused or failed consent means for C9. */
export type ConsentFailure =
  | { kind: 'otpIncorrect'; attemptsRemaining: number | undefined }
  | { kind: 'otpExpired' }
  | { kind: 'shownPlanChanged' }
  | { kind: 'consentAlreadyGiven' }
  | { kind: 'other' };

// Sorts a consent error by what the screen does next: ask again, offer a new OTP, re-show the
// plans, go to the receipt, or show a calm general message (ADR 0022 decision 3).
export function classifyConsentFailure(error: unknown): ConsentFailure {
  switch (readCustomerApiErrorCode(error)) {
    case 'OTP_INCORRECT':
      return {
        kind: 'otpIncorrect',
        attemptsRemaining: error instanceof CustomerApiError ? error.attemptsRemaining : undefined,
      };
    case 'OTP_EXPIRED':
    case 'OTP_NOT_REQUESTED':
      return { kind: 'otpExpired' };
    case 'SHOWN_PLAN_CHANGED':
      return { kind: 'shownPlanChanged' };
    case 'CONSENT_ALREADY_GIVEN':
      return { kind: 'consentAlreadyGiven' };
    default:
      return { kind: 'other' };
  }
}
