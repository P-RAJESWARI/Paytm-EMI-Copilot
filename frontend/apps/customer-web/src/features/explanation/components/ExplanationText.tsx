import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Card } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import type { HighlightedAmountKind, PlanExplanation } from '../../customer-flow';

export interface ExplanationTextProps {
  explanation: PlanExplanation;
}

const HIGHLIGHT_KEY_BY_KIND: Record<HighlightedAmountKind, string> = {
  MONTHLY_INSTALLMENT: 'explanation.monthlyAmount',
  EXTRA_IN_TOTAL: 'explanation.extraAmount',
};

// The explanation text in its own language, then its two highlighted numbers as chips; the
// numbers are the API's (the text is the server's standard template in Layer 3).
export function ExplanationText({ explanation }: ExplanationTextProps) {
  const { t } = useTranslation();
  return (
    <Card as="section" className="flex flex-col gap-3">
      <p lang={explanation.language} className="text-lead text-deep-navy">
        {explanation.text}
      </p>
      <ul aria-label={t('explanation.highlightedAmounts')} className="flex flex-wrap gap-2">
        {explanation.highlightedAmounts.map((highlightedAmount) => (
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
    </Card>
  );
}
