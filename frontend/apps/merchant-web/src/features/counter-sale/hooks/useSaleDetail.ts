import { useQuery } from '@tanstack/react-query';

import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import { buildSaleDetailQueryKey, fetchSaleDetail } from '../api/counterSaleApi';

// Reads one sale for M3; the live status feed refreshes it when the customer agrees.
export function useSaleDetail(saleId: string) {
  const { apiClient } = useMerchantApi();
  return useQuery({
    queryKey: buildSaleDetailQueryKey(saleId),
    queryFn: () => fetchSaleDetail(apiClient, saleId),
  });
}
