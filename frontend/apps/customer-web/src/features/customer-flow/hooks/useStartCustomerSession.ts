import { useQuery } from '@tanstack/react-query';

import { customerQueryKeys } from '../api/customerQueryKeys';
import { useCustomerFlowApi } from './useCustomerFlowApi';

// Trades the QR token for a session exactly once: the token is single-use, so the answer is kept
// for the page's life, never refetched and never retried (a retry would only meet a used token).
export function useStartCustomerSession(qrToken: string) {
  const customerFlowApi = useCustomerFlowApi();
  return useQuery({
    queryKey: customerQueryKeys.session(qrToken),
    queryFn: () => customerFlowApi.startSession(qrToken),
    staleTime: Infinity,
    gcTime: Infinity,
    retry: false,
    refetchOnReconnect: false,
    refetchOnWindowFocus: false,
  });
}
