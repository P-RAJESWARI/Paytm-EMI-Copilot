import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Button, Card, Chip } from '@emi-copilot/ui-kit';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import type { PlanAlternative } from '../../customer-flow';
import { PlanBandChip } from '../../../shared/plan/PlanBandChip';

export interface AlternativeDetailProps {
  alternative: PlanAlternative;
  /** Translated name, for example "No-cost EMI, 6 months, ₹4,000 down". */
  name: string;
  /** Translated one-line note under the figures. */
  note: string;
  /** Chooses this alternative here; only a longer tenure on the same item can be (ADR 0022). */
  onChoose: (() => void) | undefined;
}

/** One class for both amounts: monthly and extra in total at the same size (rule 7). */
const AMOUNT_CLASS_NAME = 'text-heading font-bold tabular-nums text-navy';

// The selected C6 alternative: monthly (with what it was) and extra in total at one size, the note,
// band and ratio, budget fit, then "Choose this plan" or "Ask the shop to set this up".
export function AlternativeDetail({ alternative, name, note, onChoose }: AlternativeDetailProps) {
  const { t } = useTranslation();
  const headingId = useId();
  const askShopKey =
    alternative.kind === 'CHEAPER_MODEL'
      ? 'alternatives.askShopCheaperModel'
      : 'alternatives.askShopDownPayment';
  return (
    <Card as="section" isHighlighted aria-labelledby={headingId} className="flex flex-col gap-3">
      <h2 id={headingId} className="text-lead font-bold">
        {name}
      </h2>
      <dl className="grid grid-cols-2 gap-2">
        <div className="flex flex-col">
          <dt className="text-label font-normal text-slate">{t('plan.eachMonth')}</dt>
          <dd className={AMOUNT_CLASS_NAME}>
            {formatRupeesFromPaise(alternative.monthlyInstallmentInPaise)}
          </dd>
          <dd className="text-caption text-slate">
            {t('alternatives.was', {
              amount: formatRupeesFromPaise(alternative.previousMonthlyInstallmentInPaise),
            })}
          </dd>
        </div>
        <div className="flex flex-col">
          <dt className="text-label font-normal text-slate">{t('plan.extraInTotal')}</dt>
          <dd className={AMOUNT_CLASS_NAME}>
            {formatRupeesFromPaise(alternative.extraInTotalInPaise)}
          </dd>
        </div>
      </dl>
      <p className="text-body text-ink-muted">{note}</p>
      <div className="flex flex-wrap gap-2">
        {alternative.comfort === null ? null : (
          <PlanBandChip comfort={alternative.comfort} isShowingRatio />
        )}
        {alternative.isWithinBudget ? <Chip>{t('plan.withinBudget')}</Chip> : null}
      </div>
      {onChoose === undefined ? (
        <div className="flex flex-col gap-1 rounded-input bg-cyan-tint p-3 text-navy">
          <p className="text-body font-bold">{t('alternatives.askShopTitle')}</p>
          <p className="text-body">{t(askShopKey)}</p>
        </div>
      ) : (
        <Button variant="secondary" onClick={onChoose}>
          {t('alternatives.chooseThisPlan')}
        </Button>
      )}
    </Card>
  );
}
