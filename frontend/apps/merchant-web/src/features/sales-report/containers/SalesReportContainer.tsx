import { SegmentedControl } from '@emi-copilot/ui-kit';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { getProblemMessageKey } from '../../../shared/api/problemMessageKey';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import { PageHeading } from '../../../shared/components/PageHeading';
import { WeeklySummaryContainer } from '../../weekly-message';
import type { ReportingRange } from '../api/salesReportApi';
import { FunnelCard } from '../components/FunnelCard';
import { SalesReportEmptyState } from '../components/SalesReportEmptyState';
import { useFunnelReport } from '../hooks/useSalesReports';
import { isFunnelEmpty } from '../model/reportCounts';
import { ReportInsightsContainer } from './ReportInsightsContainer';
import { SuggestedActionsContainer } from './SuggestedActionsContainer';

const REPORTING_RANGES: readonly ReportingRange[] = ['TODAY', 'THIS_WEEK', 'THIS_MONTH'];

// Container for M5: the period switch drives the funnel, missed sales and suggestions (money
// due is never range-filtered); a period with no sales shows the empty state instead.
export function SalesReportContainer() {
  const { t } = useTranslation();
  const [range, setRange] = useState<ReportingRange>('THIS_WEEK');
  const funnelQuery = useFunnelReport(range);
  let reportContent;
  if (funnelQuery.isPending) {
    reportContent = <LoadingSkeleton accessibleLabel={t('report.loading')} lineCount={6} />;
  } else if (funnelQuery.isError) {
    reportContent = (
      <CalmErrorMessage
        message={t(getProblemMessageKey(funnelQuery.error))}
        retryLabel={t('common.tryAgain')}
        onRetry={() => void funnelQuery.refetch()}
      />
    );
  } else if (isFunnelEmpty(funnelQuery.data)) {
    reportContent = <SalesReportEmptyState range={range} />;
  } else {
    reportContent = (
      <>
        <WeeklySummaryContainer />
        <ReportInsightsContainer
          range={range}
          leadingCard={<FunnelCard funnel={funnelQuery.data} />}
        />
        <SuggestedActionsContainer range={range} />
      </>
    );
  }
  return (
    <>
      <PageHeading
        title={t('report.title')}
        action={
          <SegmentedControl
            accessibleLabel={t('report.range.label')}
            options={REPORTING_RANGES.map((reportingRange) => ({
              value: reportingRange,
              label: t(`report.range.${reportingRange}`),
            }))}
            selectedValue={range}
            onSelectValue={setRange}
          />
        }
      />
      {reportContent}
    </>
  );
}
