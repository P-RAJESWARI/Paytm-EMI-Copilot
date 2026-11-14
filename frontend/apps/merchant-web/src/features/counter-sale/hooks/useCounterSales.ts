import { useQuery } from '@tanstack/react-query';

import { COUNTER_SALES_QUERY_KEY } from '../../../shared/api/saleQueryKeys';
import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import { fetchCounterSales } from '../api/counterSaleApi';

// Reads the "At the counter now" list; the live status feed refreshes it on every change.
export function useCounterSales() {
  const { apiClient } = useMerchantApi();
  return useQuery({
    queryKey: COUNTER_SALES_QUERY_KEY,
    queryFn: () => fetchCounterSales(apiClient),
  });
}
