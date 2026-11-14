import { QueryClient } from '@tanstack/react-query';

// Builds the TanStack Query cache for server data; one retry keeps a weak shop network usable
// without hammering the API.
export function createMerchantQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: 1 },
      mutations: { retry: false },
    },
  });
}
