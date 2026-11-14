import { FunnelBar } from '@emi-copilot/ui-kit';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import type { FunnelReport } from '../api/salesReportApi';
import { formatPossiblySuppressedCount } from '../model/reportCounts';

export interface FunnelCardProps {
  funnel: FunnelReport;
}

// "Where customers drop off": five bars from the API counts (a hidden count draws no bar and
// reads "fewer than 5") and the biggest drop the API found.
export function FunnelCard({ funnel }: FunnelCardProps) {
  const { t } = useTranslation();
  const headingId = useId();
  const visibleCounts = funnel.stages.map((stage) =>
    stage.isSuppressed ? 0 : (stage.customerCount ?? 0),
  );
  const longestBarCount = Math.max(0, ...visibleCounts);
  const biggestDrop = funnel.biggestDrop;
  let biggestDropText: string | undefined;
  if (biggestDrop !== null && biggestDrop.customerCount !== 0) {
    const stagePhrase = t(`report.funnel.afterStage.${biggestDrop.afterStage}`);
    biggestDropText =
      biggestDrop.isSuppressed || biggestDrop.customerCount === null
        ? t('report.funnel.biggestDropFew', { stagePhrase })
        : t('report.funnel.biggestDrop', { count: biggestDrop.customerCount, stagePhrase });
  }
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded-card bg-white p-6 shadow-card"
    >
      <h2 id={headingId} className="text-title text-navy">
        {t('report.funnel.title')}
      </h2>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {funnel.stages.map((stage, stageIndex) => (
          <li key={stage.stage}>
            <FunnelBar
              label={t(`report.funnel.stage.${stage.stage}`)}
              valueText={formatPossiblySuppressedCount(t, stage)}
              value={visibleCounts[stageIndex] ?? 0}
              maximumValue={longestBarCount}
              tone={stage.stage === 'PAID' ? 'success' : 'default'}
            />
          </li>
        ))}
      </ul>
      {biggestDropText === undefined ? null : (
        <p className="rounded-input bg-light-blue p-3 text-body text-deep-navy">
          {biggestDropText}
        </p>
      )}
    </section>
  );
}
