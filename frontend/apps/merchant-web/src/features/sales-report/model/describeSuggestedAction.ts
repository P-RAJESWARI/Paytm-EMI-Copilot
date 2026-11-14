import { formatRupeesFromPaise, type SupportedLanguage } from '@emi-copilot/shared-i18n';
import type { TFunction } from 'i18next';

import { formatAlternatives } from '../../../shared/formatting/formatAlternatives';
import type { SuggestedAction } from '../api/salesReportApi';

/** One suggestion as shown: a bold line and the figures behind it. */
export interface SuggestedActionText {
  title: string;
  detail: string;
}

type LongerNoCostParameters = Extract<
  SuggestedAction,
  { actionCode: 'ASK_BRAND_FOR_LONGER_NO_COST_PLAN' }
>['parameters'];

// Gives "9 or 12" for the suggested no-cost tenures, in the language's own "or".
export function formatSuggestedTenures(
  parameters: LongerNoCostParameters,
  language: SupportedLanguage,
): string {
  return formatAlternatives(
    parameters.suggestedTenures.map((suggestedTenure) => String(suggestedTenure.tenureInMonths)),
    language,
  );
}

// Writes the longer no-cost suggestion from its API figures only, never from a sum made here.
function describeLongerNoCostPlan(
  t: TFunction,
  language: SupportedLanguage,
  parameters: LongerNoCostParameters,
): SuggestedActionText {
  const title = t('report.actions.longerNoCost.title', { productName: parameters.productName });
  if (parameters.suggestedTenures.length === 0) {
    return { title, detail: '' };
  }
  const monthlyAmounts = formatAlternatives(
    parameters.suggestedTenures.map((suggestedTenure) =>
      formatRupeesFromPaise(suggestedTenure.monthlyInstallmentInPaise),
    ),
    language,
  );
  const tenureSentence = t('report.actions.longerNoCost.detail', {
    tenures: formatSuggestedTenures(parameters, language),
    monthlyAmounts,
  });
  if (parameters.budgetCeilingInPaise === null) return { title, detail: tenureSentence };
  const ceiling = formatRupeesFromPaise(parameters.budgetCeilingInPaise);
  const missedSentence =
    parameters.isMissedCustomerCountSuppressed || parameters.missedCustomerCount === null
      ? t('report.actions.longerNoCost.fewMissedCustomers', { ceiling })
      : t('report.actions.longerNoCost.missedCustomers', {
          count: parameters.missedCustomerCount,
          ceiling,
        });
  return { title, detail: `${tenureSentence} ${missedSentence}` };
}

// Writes one suggested action by its reason code, with the API's parameters filled in.
export function describeSuggestedAction(
  t: TFunction,
  language: SupportedLanguage,
  action: SuggestedAction,
): SuggestedActionText {
  if (action.actionCode === 'ASK_BRAND_FOR_LONGER_NO_COST_PLAN') {
    return describeLongerNoCostPlan(t, language, action.parameters);
  }
  return {
    title: t('report.actions.cheaperModel.title', { productName: action.parameters.productName }),
    detail: t('report.actions.cheaperModel.detail', {
      price: formatRupeesFromPaise(action.parameters.listPriceInPaise),
      monthly: formatRupeesFromPaise(action.parameters.monthlyInstallmentInPaise),
      count: action.parameters.tenureInMonths,
    }),
  };
}
