import { MerchantApiError } from '../../../shared/api/merchantApiError';
import { getProblemMessageKey } from '../../../shared/api/problemMessageKey';

/** A translation key and, for waits, the whole minutes to put in it. */
export interface PairingProblemMessage {
  translationKey: string;
  minuteCount?: number | undefined;
}

const SECONDS_PER_MINUTE = 60;

/** Pairing refusals whose message says how long to wait (from Retry-After). */
const WAIT_PROBLEM_CODES = new Set(['PAIRING_TEMPORARILY_LOCKED', 'RATE_LIMITED']);

// Chooses the calm M1 message for a failed pairing: a mismatch, a pause with its minutes, or
// the shared message for anything else (for example no network).
export function describePairingProblem(error: unknown): PairingProblemMessage {
  if (!(error instanceof MerchantApiError)) return { translationKey: getProblemMessageKey(error) };
  if (error.code === 'INVALID_PAIRING_CREDENTIALS') {
    return { translationKey: 'pairing.problems.INVALID_PAIRING_CREDENTIALS' };
  }
  if (WAIT_PROBLEM_CODES.has(error.code) && error.retryAfterInSeconds !== undefined) {
    return {
      translationKey: `pairing.problems.${error.code}`,
      minuteCount: Math.max(1, Math.ceil(error.retryAfterInSeconds / SECONDS_PER_MINUTE)),
    };
  }
  return { translationKey: getProblemMessageKey(error) };
}
