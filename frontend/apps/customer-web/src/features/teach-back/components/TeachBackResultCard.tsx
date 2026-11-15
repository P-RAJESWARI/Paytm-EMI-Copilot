import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Button, Card } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import type { HighlightedAmountKind, TeachBackOutcome } from '../../customer-flow';

export interface TeachBackResultCardProps {
  outcome: TeachBackOutcome;
  onExplainAgain: () => void;
}

const HIGHLIGHT_KEY_BY_KIND: Record<HighlightedAmountKind, string> = {
  MONTHLY_INSTALLMENT: 'teachBack.monthlyAmount',
  EXTRA_IN_TOTAL: 'teachBack.extraAmount',
};

// C8's result: the server's title and body, what it heard, the plan's numbers as chips and, when
// the answer was not close, "Explain it again". It never blocks continuing.
export function TeachBackResultCard({ outcome, onExplainAgain }: TeachBackResultCardProps) {
  const { t } = useTranslation();
  return (
    <Card as="section" className="flex flex-col gap-3">
      <h2 className="text-lead font-bold text-deep-navy">{outcome.title}</h2>
      <p className="text-body text-deep-navy">{outcome.body}</p>
      {outcome.heardText === null ? null : (
        <p className="text-body text-slate">
          {t('teachBack.heardLabel')} <span className="text-deep-navy">{outcome.heardText}</span>
        </p>
      )}
      <ul aria-label={t('teachBack.highlightedAmounts')} className="flex flex-wrap gap-2">
        {outcome.highlightedAmounts.map((highlightedAmount) => (
          <li
            key={highlightedAmount.kind}
            className={`rounded-input px-3 py-2 text-body font-bold tabular-nums ${
              highlightedAmount.kind === 'EXTRA_IN_TOTAL' && highlightedAmount.amountInPaise === 0
                ? 'bg-comfortable-tint text-comfortable-text'
                : 'bg-light-blue text-navy'
            }`}
          >
            {t(HIGHLIGHT_KEY_BY_KIND[highlightedAmount.kind], {
              amount: formatRupeesFromPaise(highlightedAmount.amountInPaise),
            })}
          </li>
        ))}
      </ul>
      {outcome.result === 'TRY_AGAIN' ? (
        <Button variant="secondary" className="self-start" onClick={onExplainAgain}>
          {t('teachBack.explainAgain')}
        </Button>
      ) : null}
    </Card>
  );
}
