import { createRandomCorrelationId } from '@emi-copilot/api-client';

// Makes a fresh Idempotency-Key (a random UUID v4) for one user intent, such as one
// "Show QR to customer" click; retrying the same intent re-sends the same key.
export function createIdempotencyKey(): string {
  return createRandomCorrelationId();
}
