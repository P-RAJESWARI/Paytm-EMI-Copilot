import type { SupportedLanguage } from '@emi-copilot/shared-i18n';

import type { ComfortCheckStatus } from './customerContractTypes';

/** Root of every customer query key, so one session's data can be dropped together. */
const CUSTOMER_QUERY_KEY_ROOT = 'customer';

// TanStack Query keys of the customer flow. Each key names every answer the server's reply
// depends on, so a changed budget, comfort choice, plan or language fetches afresh.
export const customerQueryKeys = {
  session: (qrToken: string) => [CUSTOMER_QUERY_KEY_ROOT, 'session', qrToken] as const,
  /** Every plans query, so a changed plan (409 SHOWN_PLAN_CHANGED) refetches them all. */
  plansRoot: () => [CUSTOMER_QUERY_KEY_ROOT, 'plans'] as const,
  plans: (monthlyBudgetInPaise: number, comfortCheckStatus: ComfortCheckStatus) =>
    [CUSTOMER_QUERY_KEY_ROOT, 'plans', monthlyBudgetInPaise, comfortCheckStatus] as const,
  /** Every alternatives query, refetched with the plans when a plan's figures changed. */
  alternativesRoot: () => [CUSTOMER_QUERY_KEY_ROOT, 'alternatives'] as const,
  alternatives: (offerId: string, monthlyBudgetInPaise: number) =>
    [CUSTOMER_QUERY_KEY_ROOT, 'alternatives', offerId, monthlyBudgetInPaise] as const,
  explanation: (offerId: string, language: SupportedLanguage) =>
    [CUSTOMER_QUERY_KEY_ROOT, 'explanation', offerId, language] as const,
  receipt: () => [CUSTOMER_QUERY_KEY_ROOT, 'receipt'] as const,
};
