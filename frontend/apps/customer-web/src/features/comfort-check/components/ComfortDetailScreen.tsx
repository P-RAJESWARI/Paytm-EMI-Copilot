import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Button, Card } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import type { ComfortCheckResult, PlanComfortResponse } from '../../customer-flow';
import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { ScreenTitle } from '../../../shared/components/ScreenTitle';
import { formatPercentFromBasisPoints } from '../../../shared/formatting/formatPercentFromBasisPoints';
import { PlanBandChip } from '../../../shared/plan/PlanBandChip';
import { ComfortShareBar } from './ComfortShareBar';
import { ComfortPlanHeader, type ComfortPlanHeaderProps } from './ComfortPlanHeader';

export interface ComfortDetailScreenProps {
  plan: ComfortPlanHeaderProps['plan'] & { comfort: PlanComfortResponse };
  comfortCheck: ComfortCheckResult;
  onBack: () => void;
}

// C5: one plan's band, what share of the monthly inflow it and the current EMIs take, the bar,
// and how to read the bands. Every number is the API's; this screen only formats them.
export function ComfortDetailScreen({ plan, comfortCheck, onBack }: ComfortDetailScreenProps) {
  const { t } = useTranslation();
  const { comfort } = plan;
  const shareRows = [
    {
      label: t('comfortDetail.currentEmis'),
      amountInPaise: comfortCheck.existingEmisInPaise,
      shareInBasisPoints: comfort.existingEmisShareInBasisPoints,
    },
    {
      label: t('comfortDetail.thisPlan'),
      amountInPaise: plan.monthlyInstallmentInPaise,
      shareInBasisPoints: comfort.planShareInBasisPoints,
    },
  ];
  return (
    <ScreenLayout
      onBack={onBack}
      footer={
        <Button variant="secondary" size="large" isFullWidth onClick={onBack}>
          {t('comfortDetail.backToPlans')}
        </Button>
      }
    >
      <ScreenTitle>{t('comfortDetail.heading')}</ScreenTitle>
      <ComfortPlanHeader plan={plan} />
      <Card className="flex flex-col gap-3">
        <div>
          <PlanBandChip comfort={comfort} />
        </div>
        <p className="text-body font-semibold">
          {t('comfortDetail.withThisPlan', {
            percent: formatPercentFromBasisPoints(comfort.comfortRatioInBasisPoints),
          })}
        </p>
        <p className="text-body text-slate">
          {t('comfortDetail.currentShare', {
            percent: formatPercentFromBasisPoints(comfort.existingEmisShareInBasisPoints),
          })}
        </p>
        <ComfortShareBar
          band={comfort.band}
          existingEmisShareInBasisPoints={comfort.existingEmisShareInBasisPoints}
          planShareInBasisPoints={comfort.planShareInBasisPoints}
          comfortRatioInBasisPoints={comfort.comfortRatioInBasisPoints}
        />
        <dl className="flex flex-col gap-2 text-body">
          {shareRows.map((row) => (
            <div key={row.label} className="flex justify-between gap-2">
              <dt className="text-slate">{row.label}</dt>
              <dd className="font-bold tabular-nums">
                {row.amountInPaise === null
                  ? formatPercentFromBasisPoints(row.shareInBasisPoints)
                  : t('comfortDetail.amountWithShare', {
                      amount: formatRupeesFromPaise(row.amountInPaise),
                      percent: formatPercentFromBasisPoints(row.shareInBasisPoints),
                    })}
              </dd>
            </div>
          ))}
          {comfortCheck.monthlyInflowInPaise === null ? null : (
            <div className="flex justify-between gap-2">
              <dt className="text-slate">{t('comfortDetail.inflow')}</dt>
              <dd className="font-bold tabular-nums">
                {formatRupeesFromPaise(comfortCheck.monthlyInflowInPaise)}
              </dd>
            </div>
          )}
        </dl>
      </Card>
      <Card surface="soft" className="flex flex-col gap-2">
        <h2 className="text-body font-bold text-navy">{t('comfortDetail.howTitle')}</h2>
        <ul className="flex list-disc flex-col gap-1 pl-6 text-body">
          <li>{t('comfortDetail.belowLower')}</li>
          <li>{t('comfortDetail.betweenLowerAndUpper')}</li>
          <li>{t('comfortDetail.aboveUpper')}</li>
        </ul>
        <p className="text-label font-normal text-ink-muted">{t('comfortDetail.guide')}</p>
      </Card>
    </ScreenLayout>
  );
}
