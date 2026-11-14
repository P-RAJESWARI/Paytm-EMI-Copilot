import type { Middleware } from 'openapi-fetch';

import { createRandomCorrelationId } from './createRandomCorrelationId';

export const CORRELATION_ID_HEADER = 'X-Correlation-Id';

// Gives every request its own X-Correlation-Id (api-conventions.md section 5) unless the caller set one.
export function createCorrelationIdMiddleware(
  createCorrelationId: () => string = createRandomCorrelationId,
): Middleware {
  return {
    onRequest({ request }) {
      if (!request.headers.has(CORRELATION_ID_HEADER)) {
        request.headers.set(CORRELATION_ID_HEADER, createCorrelationId());
      }
      return request;
    },
  };
}
