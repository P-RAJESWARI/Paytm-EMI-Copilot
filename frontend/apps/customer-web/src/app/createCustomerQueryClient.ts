import { QueryClient } from '@tanstack/react-query';

import { CustomerApiError } from '../features/customer-flow';

const MAXIMUM_QUERY_RETRY_COUNT = 1;

// Retries a failed read once, except when the server already said no (any 4xx answer).
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  const isRefusedByServer =
    error instanceof CustomerApiError && error.status >= 400 && error.status < 500;
  return !isRefusedByServer && failureCount < MAXIMUM_QUERY_RETRY_COUNT;
}

// Builds the TanStack Query cache for the customer's server data. One retry helps a weak phone
// signal; mutations (budget, consent, OTP) never retry by themselves, and nothing refetches just
// because the customer switched apps, so a POST read such as the explanation is not repeated.
export function createCustomerQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetryQuery, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
}
