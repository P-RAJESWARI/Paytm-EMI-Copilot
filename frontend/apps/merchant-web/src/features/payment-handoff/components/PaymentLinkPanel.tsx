import { Button, QrPanel } from '@emi-copilot/ui-kit';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import type { CopyState } from '../../../shared/clipboard/useCopyToClipboard';

export interface PaymentLinkPanelProps {
  paymentUrl: string;
  onCopyLink: () => void;
  copyState: CopyState;
}

// The payment link shown on the tablet as a QR code with a copy button (plan Q6): nothing is
// sent from here; the customer scans it and pays on Paytm.
export function PaymentLinkPanel({ paymentUrl, onCopyLink, copyState }: PaymentLinkPanelProps) {
  const { t } = useTranslation();
  const linkInputId = useId();
  return (
    <section aria-label={t('handoff.link.title')} className="flex flex-col gap-3">
      <QrPanel
        value={paymentUrl}
        accessibleLabel={t('handoff.link.qrLabel')}
        title={t('handoff.link.title')}
        caption={t('handoff.link.caption')}
        layout="inline"
      />
      <label htmlFor={linkInputId} className="text-label">
        {t('handoff.link.urlLabel')}
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <input
          id={linkInputId}
          readOnly
          value={paymentUrl}
          onFocus={(event) => {
            event.target.select();
          }}
          className="min-h-touch-target min-w-0 flex-1 rounded-input border border-border bg-white px-3 text-label font-normal text-deep-navy"
        />
        <Button variant="secondary" onClick={onCopyLink}>
          {t('handoff.link.copy')}
        </Button>
      </div>
      <p role="status" className="text-label font-normal text-slate">
        {copyState === 'copied' ? t('handoff.link.copied') : null}
        {copyState === 'unavailable' ? t('handoff.link.copyUnavailable') : null}
      </p>
    </section>
  );
}
