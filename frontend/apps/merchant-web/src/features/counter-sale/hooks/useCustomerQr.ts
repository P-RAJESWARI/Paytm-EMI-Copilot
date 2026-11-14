import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import { buildCustomerQrQueryKey, issueCustomerQr } from '../api/counterSaleApi';

// Gives the sale's QR code from memory, or issues one when none is held (for example after
// opening M3 from the counter list). Issuing voids the previous code, so it never happens on
// its own again: no refetch on focus, reconnect or remount. "Show a new QR" issues explicitly.
export function useCustomerQr(saleId: string, isSaleChoosing: boolean) {
  const { apiClient } = useMerchantApi();
  const queryClient = useQueryClient();
  const customerQrQuery = useQuery({
    queryKey: buildCustomerQrQueryKey(saleId),
    queryFn: () => issueCustomerQr(apiClient, saleId),
    enabled: isSaleChoosing,
    staleTime: Infinity,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    retry: false,
  });
  const issueNewQrMutation = useMutation({
    mutationFn: () => issueCustomerQr(apiClient, saleId),
    onSuccess: (customerQr) => {
      queryClient.setQueryData(buildCustomerQrQueryKey(saleId), customerQr);
    },
  });
  return { customerQrQuery, issueNewQrMutation };
}
