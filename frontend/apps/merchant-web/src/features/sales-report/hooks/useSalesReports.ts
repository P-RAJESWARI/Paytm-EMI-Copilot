import { useQuery } from '@tanstack/react-query';

import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import {
  MONEY_DUE_QUERY_KEY,
  buildReportQueryKey,
  fetchFunnelReport,
  fetchMissedSalesReport,
  fetchMoneyDue,
  fetchSuggestedActions,
  type ReportingRange,
} from '../api/salesReportApi';

// Reads the funnel for the chosen range; M5 uses it to decide between the report and the empty state.
export function useFunnelReport(range: ReportingRange) {
  const { apiClient } = useMerchantApi();
  return useQuery({
    queryKey: buildReportQueryKey('funnel', range),
    queryFn: () => fetchFunnelReport(apiClient, range),
  });
}

// Reads the missed sales and budget buckets for the chosen range.
export function useMissedSalesReport(range: ReportingRange) {
  const { apiClient } = useMerchantApi();
  return useQuery({
    queryKey: buildReportQueryKey('missed-sales', range),
    queryFn: () => fetchMissedSalesReport(apiClient, range),
  });
}

// Reads the suggested actions for the chosen range; the missed-sales panel and the list share it.
export function useSuggestedActions(range: ReportingRange) {
  const { apiClient } = useMerchantApi();
  return useQuery({
    queryKey: buildReportQueryKey('suggested-actions', range),
    queryFn: () => fetchSuggestedActions(apiClient, range),
  });
}

// Reads the money due from brands, which no range filters.
export function useMoneyDue() {
  const { apiClient } = useMerchantApi();
  return useQuery({ queryKey: MONEY_DUE_QUERY_KEY, queryFn: () => fetchMoneyDue(apiClient) });
}
