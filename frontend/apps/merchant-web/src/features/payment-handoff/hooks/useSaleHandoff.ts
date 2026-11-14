import { useQuery } from '@tanstack/react-query';

import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import { buildSaleHandoffQueryKey, fetchSaleHandoff } from '../api/paymentHandoffApi';

// Reads M4's hand-off; the live status feed refreshes it when the payment is confirmed.
export function useSaleHandoff(saleId: string) {
  const { apiClient } = useMerchantApi();
  return useQuery({
    queryKey: buildSaleHandoffQueryKey(saleId),
    queryFn: () => fetchSaleHandoff(apiClient, saleId),
  });
}
