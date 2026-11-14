import { formatRupeesFromPaise, type SupportedLanguage } from '@emi-copilot/shared-i18n';
import type { TFunction } from 'i18next';

import type { MissedSalesReport, SuggestedAction } from '../api/salesReportApi';
import { formatSuggestedTenures } from './describeSuggestedAction';
import { formatPossiblySuppressedCount } from './reportCounts';

export interface BrandRepShareFacts {
  shopName: string;
  /** Translated period, for example "This week". */
  periodLabel: string;
  missedSales: MissedSalesReport;
  suggestedActions: readonly SuggestedAction[];
}

// Writes the ask for a longer no-cost plan, when the API suggested tenures for it.
function buildLongerNoCostRequest(
  t: TFunction,
  language: SupportedLanguage,
  suggestedActions: readonly SuggestedAction[],
): string | undefined {
  const longerNoCostAction = suggestedActions.find(
    (action) => action.actionCode === 'ASK_BRAND_FOR_LONGER_NO_COST_PLAN',
  );
  if (
    longerNoCostAction === undefined ||
    longerNoCostAction.parameters.suggestedTenures.length === 0
  ) {
    return undefined;
  }
  return t('report.share.request', {
    tenures: formatSuggestedTenures(longerNoCostAction.parameters, language),
  });
}

// Writes the "Share with brand rep" text in the shop language from report figures only; it is
// copied to the clipboard, never sent by the app. Gives undefined when there is nothing to share.
export function buildBrandRepShareText(
  t: TFunction,
  language: SupportedLanguage,
  facts: BrandRepShareFacts,
): string | undefined {
  const { missedSales } = facts;
  if (missedSales.productInsight === null || missedSales.budgetCeilingInPaise === null)
    return undefined;
  const summary = t('report.share.summary', {
    shopName: facts.shopName,
    periodLabel: facts.periodLabel,
    customerCount: formatPossiblySuppressedCount(t, {
      customerCount: missedSales.missedCustomerCount,
      isSuppressed: missedSales.isSuppressed,
    }),
    productName: missedSales.productInsight.productName,
    ceiling: formatRupeesFromPaise(missedSales.budgetCeilingInPaise),
    lowestMonthly: formatRupeesFromPaise(
      missedSales.productInsight.lowestNoExtraCostMonthlyInPaise,
    ),
  });
  const request = buildLongerNoCostRequest(t, language, facts.suggestedActions);
  return request === undefined ? summary : `${summary} ${request}`;
}
