import { ExpandableCardButton, ExpandableCardPanel } from '@emi-copilot/ui-kit';
import { useId, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { getProblemMessageKey } from '../../../shared/api/problemMessageKey';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import type { ReportingRange } from '../api/salesReportApi';
import { BrandRepShare } from '../components/BrandRepShare';
import { MissedSalesPanelContent } from '../components/MissedSalesPanelContent';
import { MissedSalesSummary } from '../components/MissedSalesSummary';
import { MoneyDuePanelContent } from '../components/MoneyDuePanelContent';
import { MoneyDueSummary } from '../components/MoneyDueSummary';
import { useBrandRepShare } from '../hooks/useBrandRepShare';
import { useMissedSalesReport, useMoneyDue, useSuggestedActions } from '../hooks/useSalesReports';

type OpenPanel = 'missedSales' | 'moneyDue' | undefined;

export interface ReportInsightsContainerProps {
  range: ReportingRange;
  /** The funnel card, laid out beside the two expandable cards as on M5. */
  leadingCard: ReactNode;
}

// Container for M5's "Missed sales" and "Money due from brands" cards: an accordion (one open
// at a time) whose detail opens in place below the grid (M6, M7), plus the brand-rep share.
export function ReportInsightsContainer({ range, leadingCard }: ReportInsightsContainerProps) {
  const { t } = useTranslation();
  const [openPanel, setOpenPanel] = useState<OpenPanel>(undefined);
  const missedSalesPanelId = useId();
  const moneyDuePanelId = useId();
  const missedSalesQuery = useMissedSalesReport(range);
  const moneyDueQuery = useMoneyDue();
  const suggestedActionsQuery = useSuggestedActions(range);
  const { suggestedActionText, shareText, copyState, copyText } = useBrandRepShare(
    range,
    missedSalesQuery.data,
    suggestedActionsQuery.data ?? [],
  );

  // Opens the chosen card, or closes it when it is already open.
  function togglePanel(panel: Exclude<OpenPanel, undefined>) {
    setOpenPanel((currentPanel) => (currentPanel === panel ? undefined : panel));
  }

  // Shows a card's loading or error state in its place in the grid.
  function renderCardPlaceholder(query: {
    isPending: boolean;
    error: unknown;
    refetch: () => unknown;
  }) {
    if (query.isPending) return <LoadingSkeleton accessibleLabel={t('common.loading')} />;
    return (
      <CalmErrorMessage
        message={t(getProblemMessageKey(query.error))}
        retryLabel={t('common.tryAgain')}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const expandLabels = {
    showDetailsLabel: t('common.seeDetails'),
    hideDetailsLabel: t('common.hideDetails'),
  };
  return (
    <>
      <div className="grid gap-4 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        {leadingCard}
        <div className="flex flex-col gap-4">
          {missedSalesQuery.data === undefined ? (
            renderCardPlaceholder(missedSalesQuery)
          ) : (
            <ExpandableCardButton
              panelId={missedSalesPanelId}
              isExpanded={openPanel === 'missedSales'}
              onToggle={() => {
                togglePanel('missedSales');
              }}
              {...expandLabels}
            >
              <MissedSalesSummary missedSales={missedSalesQuery.data} />
            </ExpandableCardButton>
          )}
          {moneyDueQuery.data === undefined ? (
            renderCardPlaceholder(moneyDueQuery)
          ) : (
            <ExpandableCardButton
              panelId={moneyDuePanelId}
              isExpanded={openPanel === 'moneyDue'}
              onToggle={() => {
                togglePanel('moneyDue');
              }}
              {...expandLabels}
            >
              <MoneyDueSummary moneyDue={moneyDueQuery.data} />
            </ExpandableCardButton>
          )}
        </div>
      </div>
      <ExpandableCardPanel
        id={missedSalesPanelId}
        isExpanded={openPanel === 'missedSales'}
        accessibleLabel={t('report.missedSales.panelLabel')}
      >
        {missedSalesQuery.data === undefined ? null : (
          <MissedSalesPanelContent
            missedSales={missedSalesQuery.data}
            suggestedActionText={suggestedActionText}
            shareControl={
              shareText === undefined ? null : (
                <BrandRepShare
                  shareText={shareText}
                  copyState={copyState}
                  onShare={() => void copyText(shareText)}
                />
              )
            }
          />
        )}
      </ExpandableCardPanel>
      <ExpandableCardPanel
        id={moneyDuePanelId}
        isExpanded={openPanel === 'moneyDue'}
        accessibleLabel={t('report.moneyDue.panelLabel')}
      >
        {moneyDueQuery.data === undefined ? null : (
          <MoneyDuePanelContent moneyDue={moneyDueQuery.data} />
        )}
      </ExpandableCardPanel>
    </>
  );
}
