import type { ApiSchemas, BackendApiClient } from '@emi-copilot/api-client';

import { readApiData } from '../../../shared/api/readApiData';

export type ReportingRange = ApiSchemas['ReportingRange'];
export type FunnelReport = ApiSchemas['FunnelReportResponse'];
export type MissedSalesReport = ApiSchemas['MissedSalesReportResponse'];
export type SuggestedAction = ApiSchemas['SuggestedActionsResponse']['actions'][number];
export type MoneyDueReport = ApiSchemas['MoneyDueResponse'];
export type BudgetBucket = ApiSchemas['BudgetBucketResponse'];

const REPORT_QUERY_KEY_ROOT = 'report';

// Gives the query key of one range-filtered report, for example the funnel for THIS_WEEK.
export function buildReportQueryKey(
  reportName: 'funnel' | 'missed-sales' | 'suggested-actions',
  range: ReportingRange,
): readonly [string, string, ReportingRange] {
  return [REPORT_QUERY_KEY_ROOT, reportName, range];
}

/** Money due is never range-filtered (plan Q13). */
export const MONEY_DUE_QUERY_KEY = [REPORT_QUERY_KEY_ROOT, 'money-due'] as const;

// Reads "Where customers drop off" for the range (GET /reports/funnel).
export function fetchFunnelReport(
  apiClient: BackendApiClient,
  range: ReportingRange,
): Promise<FunnelReport> {
  return readApiData(apiClient.GET('/api/v1/reports/funnel', { params: { query: { range } } }));
}

// Reads the missed sales and budget buckets for the range (GET /reports/missed-sales).
export function fetchMissedSalesReport(
  apiClient: BackendApiClient,
  range: ReportingRange,
): Promise<MissedSalesReport> {
  return readApiData(
    apiClient.GET('/api/v1/reports/missed-sales', { params: { query: { range } } }),
  );
}

// Reads "What you can do to sell more" as reason codes with figures (GET /reports/suggested-actions).
export async function fetchSuggestedActions(
  apiClient: BackendApiClient,
  range: ReportingRange,
): Promise<SuggestedAction[]> {
  const suggestedActionsResponse = await readApiData(
    apiClient.GET('/api/v1/reports/suggested-actions', { params: { query: { range } } }),
  );
  return suggestedActionsResponse.actions;
}

// Reads what brands still owe the shop (GET /reports/money-due), from the labelled Mock settlement.
export function fetchMoneyDue(apiClient: BackendApiClient): Promise<MoneyDueReport> {
  return readApiData(apiClient.GET('/api/v1/reports/money-due'));
}
