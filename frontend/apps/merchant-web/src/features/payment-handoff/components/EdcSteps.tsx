import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Button } from '@emi-copilot/ui-kit';
import { useId } from 'react';
import { Trans, useTranslation } from 'react-i18next';

import type { SaleHandoff } from '../api/paymentHandoffApi';

export interface EdcStepsProps {
  edcInstructions: SaleHandoff['edcInstructions'];
  onSendPaymentLink: () => void;
  isSendingPaymentLink: boolean;
  /** False while a link is open or the sale is paid, so no second link is asked for. */
  canSendPaymentLink: boolean;
}

const BOLD_COMPONENTS = { strong: <strong className="font-bold text-deep-navy" /> };

// The card-machine steps (Q5: instructions only, the server never marks an EDC sale paid) and
// the "No EDC at hand? Send payment link" fallback.
export function EdcSteps({
  edcInstructions,
  onSendPaymentLink,
  isSendingPaymentLink,
  canSendPaymentLink,
}: EdcStepsProps) {
  const { t } = useTranslation();
  const headingId = useId();
  const tenureKey = edcInstructions.isNoExtraCost
    ? 'handoff.edc.tenureNoCost'
    : 'handoff.edc.tenure';
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-4 rounded-card bg-white p-6 shadow-card"
    >
      <h2 id={headingId} className="text-title text-navy">
        {t('handoff.edc.title')}
      </h2>
      <ol className="m-0 flex list-decimal flex-col gap-2 pl-6 text-body text-deep-navy">
        <li>
          <Trans
            i18nKey="handoff.edc.stepChooseProgramme"
            values={{ programme: t(`handoff.edc.programme.${edcInstructions.emiProgramme}`) }}
            components={BOLD_COMPONENTS}
          />
        </li>
        <li>
          <Trans
            i18nKey="handoff.edc.stepPickProduct"
            values={{
              productName: edcInstructions.productName,
              tenure: t(tenureKey, { count: edcInstructions.tenureInMonths }),
            }}
            components={BOLD_COMPONENTS}
          />
        </li>
        <li>
          <Trans
            i18nKey="handoff.edc.stepCheckAmount"
            values={{ amount: formatRupeesFromPaise(edcInstructions.amountInPaise) }}
            components={BOLD_COMPONENTS}
          />
        </li>
      </ol>
      <div className="flex flex-wrap items-center gap-3 border-t border-border pt-4">
        <span className="text-body text-slate">{t('handoff.link.noEdc')}</span>
        <Button
          variant="secondary"
          onClick={onSendPaymentLink}
          disabled={!canSendPaymentLink || isSendingPaymentLink}
        >
          {isSendingPaymentLink ? t('handoff.link.sending') : t('handoff.link.send')}
        </Button>
      </div>
    </section>
  );
}
