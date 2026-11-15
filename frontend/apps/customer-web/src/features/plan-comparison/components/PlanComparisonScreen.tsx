import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Button } from '@emi-copilot/ui-kit';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { ScreenTitle } from '../../../shared/components/ScreenTitle';

export interface PlanComparisonScreenProps {
  productName: string;
  priceInPaise: number;
  /** The sort note, already translated; undefined while the plans load. */
  sortNote: string | undefined;
  /** True after consent found the shown figures changed; C4 then says so once. */
  hasShownPlanChanged: boolean;
  hasSelectedPlan: boolean;
  /** The plans, or the loading, empty or error state. */
  children: ReactNode;
  onContinue: () => void;
  onBack: () => void;
}

// C4's frame: title, the item and price, the sort note, the plans, and Continue (once a plan is
// selected; nothing is selected for the customer).
export function PlanComparisonScreen({
  productName,
  priceInPaise,
  sortNote,
  hasShownPlanChanged,
  hasSelectedPlan,
  children,
  onContinue,
  onBack,
}: PlanComparisonScreenProps) {
  const { t } = useTranslation();
  return (
    <ScreenLayout
      onBack={onBack}
      stepLabel={t('flow.stepOf', { current: 3, total: 4 })}
      footer={
        <>
          {hasSelectedPlan ? null : (
            <p className="text-label font-normal text-slate">{t('plans.chooseToContinue')}</p>
          )}
          <Button size="large" isFullWidth onClick={onContinue} disabled={!hasSelectedPlan}>
            {t('plans.continue')}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-1">
        <ScreenTitle>{t('plans.title')}</ScreenTitle>
        <p className="text-body text-slate">
          {t('plans.productLine', { productName, price: formatRupeesFromPaise(priceInPaise) })}
        </p>
        {sortNote === undefined ? null : <p className="text-label text-navy">{sortNote}</p>}
      </div>
      {hasShownPlanChanged ? (
        <p role="status" className="rounded-input bg-cyan-tint p-3 text-body text-navy">
          {t('plans.planChanged')}
        </p>
      ) : null}
      {children}
    </ScreenLayout>
  );
}
