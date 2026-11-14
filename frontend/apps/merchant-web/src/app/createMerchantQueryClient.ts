import { QueryClient } from '@tanstack/react-query';

import { MerchantApiError } from '../shared/api/merchantApiError';

const MAXIMUM_QUERY_RETRY_COUNT = 1;

// Retries a failed read once, except when the server already said no (any 4xx answer):
// asking again would only repeat the same answer.
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  const isRefusedByServer =
    error instanceof MerchantApiError && error.status >= 400 && error.status < 500;
  return !isRefusedByServer && failureCount < MAXIMUM_QUERY_RETRY_COUNT;
}

// Builds the TanStack Query cache for server data; one retry keeps a weak shop network usable
// without hammering the API. Mutations (sales, links, sending) are never retried automatically.
export function createMerchantQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetryQuery },
      mutations: { retry: false },
    },
  });
}
