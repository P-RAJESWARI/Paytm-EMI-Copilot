import { useLanguagePreference } from '@emi-copilot/shared-i18n';
import { useTranslation } from 'react-i18next';

import { getProblemMessageKey } from '../../../shared/api/problemMessageKey';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import type { ReportingRange } from '../api/salesReportApi';
import { SuggestedActionsCard } from '../components/SuggestedActionsCard';
import { useSuggestedActions } from '../hooks/useSalesReports';
import { describeSuggestedAction } from '../model/describeSuggestedAction';

export interface SuggestedActionsContainerProps {
  range: ReportingRange;
}

// Container for "What you can do to sell more": turns each reason code into translated text.
export function SuggestedActionsContainer({ range }: SuggestedActionsContainerProps) {
  const { t } = useTranslation();
  const { selectedLanguage } = useLanguagePreference();
  const suggestedActionsQuery = useSuggestedActions(range);
  if (suggestedActionsQuery.isPending)
    return <LoadingSkeleton accessibleLabel={t('common.loading')} />;
  if (suggestedActionsQuery.isError) {
    return (
      <CalmErrorMessage
        message={t(getProblemMessageKey(suggestedActionsQuery.error))}
        retryLabel={t('common.tryAgain')}
        onRetry={() => void suggestedActionsQuery.refetch()}
      />
    );
  }
  return (
    <SuggestedActionsCard
      actions={suggestedActionsQuery.data.map((action) =>
        describeSuggestedAction(t, selectedLanguage, action),
      )}
    />
  );
}
