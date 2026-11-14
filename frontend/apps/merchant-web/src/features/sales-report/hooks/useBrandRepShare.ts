import { useLanguagePreference } from '@emi-copilot/shared-i18n';
import { useTranslation } from 'react-i18next';

import { useCopyToClipboard } from '../../../shared/clipboard/useCopyToClipboard';
import { useMerchantProfile } from '../../../shared/session/useMerchantProfile';
import type { MissedSalesReport, ReportingRange, SuggestedAction } from '../api/salesReportApi';
import { buildBrandRepShareText } from '../model/buildBrandRepShareText';
import { formatSuggestedTenures } from '../model/describeSuggestedAction';

// Prepares the missed-sales panel's suggested action ("Ask the brand for a 9 or 12-month…") and
// the brand-rep text with its copy state, all in the shop language from report figures.
export function useBrandRepShare(
  range: ReportingRange,
  missedSales: MissedSalesReport | undefined,
  suggestedActions: readonly SuggestedAction[],
) {
  const { t } = useTranslation();
  const { selectedLanguage } = useLanguagePreference();
  const { data: merchantProfile } = useMerchantProfile();
  const { copyState, copyText } = useCopyToClipboard();
  const longerNoCostAction = suggestedActions.find(
    (action) => action.actionCode === 'ASK_BRAND_FOR_LONGER_NO_COST_PLAN',
  );
  const suggestedActionText =
    longerNoCostAction === undefined || longerNoCostAction.parameters.suggestedTenures.length === 0
      ? undefined
      : t('report.missedSales.askBrand', {
          tenures: formatSuggestedTenures(longerNoCostAction.parameters, selectedLanguage),
        });
  const shareText =
    missedSales === undefined
      ? undefined
      : buildBrandRepShareText(t, selectedLanguage, {
          shopName: merchantProfile?.shopName ?? '',
          periodLabel: t(`report.range.${range}`),
          missedSales,
          suggestedActions,
        });
  return { suggestedActionText, shareText, copyState, copyText };
}
