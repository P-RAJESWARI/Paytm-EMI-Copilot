import { createRandomCorrelationId } from '@emi-copilot/api-client';
import { useRef } from 'react';

import { isRequestOutcomeUnknown } from '../api/customerApiError';

/** The key last sent for one intent, kept while the server's answer to it is unknown. */
interface KeptIdempotencyKey {
  intentId: string;
  idempotencyKey: string;
}

/** Hands out and retires the Idempotency-Key of one kind of customer intent. */
export interface IdempotencyKeyPerIntent {
  takeIdempotencyKey: (intentId: string) => string;
  settleIdempotencyKey: (idempotencyKey: string, error: unknown) => void;
}

// Gives each consent intent its Idempotency-Key (api-conventions.md section 5), as merchant-web
// does: a retry re-sends the key only while the last outcome is unknown (no answer, or a 5xx
// without a problem body); any definite answer, such as a wrong OTP, retires the key.
export function useIdempotencyKeyPerIntent(): IdempotencyKeyPerIntent {
  const keptKey = useRef<KeptIdempotencyKey | undefined>(undefined);

  // Gives the key to send: the kept one for a retry of the same intent, otherwise a fresh one.
  function takeIdempotencyKey(intentId: string): string {
    if (keptKey.current?.intentId !== intentId) {
      keptKey.current = { intentId, idempotencyKey: createRandomCorrelationId() };
    }
    return keptKey.current.idempotencyKey;
  }

  // Records how a request ended (error is null on success); only an unknown outcome keeps its key.
  function settleIdempotencyKey(idempotencyKey: string, error: unknown): void {
    if (keptKey.current?.idempotencyKey !== idempotencyKey) return;
    if (error === null || !isRequestOutcomeUnknown(error)) keptKey.current = undefined;
  }

  return { takeIdempotencyKey, settleIdempotencyKey };
}
