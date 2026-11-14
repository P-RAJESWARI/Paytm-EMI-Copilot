import { Button, QrPanel } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import type { CustomerQr } from '../api/counterSaleApi';

export interface CustomerQrAreaProps {
  sessionCode: string;
  /** Only a sale that is still CHOOSING shows a QR code. */
  isSaleChoosing: boolean;
  customerQr: CustomerQr | undefined;
  isQrLoading: boolean;
  /** Translated, calm message when the QR could not be issued. */
  qrProblemMessage?: string | undefined;
  isQrExpired: boolean;
  onShowNewQr: () => void;
  isIssuingNewQr: boolean;
}

// M3's left side: the QR code with "Opens on their phone", or its loading, problem and expired
// states with "Show a new QR"; once the customer agreed, a note that no QR is needed.
export function CustomerQrArea({
  sessionCode,
  isSaleChoosing,
  customerQr,
  isQrLoading,
  qrProblemMessage,
  isQrExpired,
  onShowNewQr,
  isIssuingNewQr,
}: CustomerQrAreaProps) {
  const { t } = useTranslation();
  if (!isSaleChoosing) {
    return (
      <p className="rounded-card bg-white p-6 text-body text-slate">{t('showQr.qrNotNeeded')}</p>
    );
  }
  const showNewQrButton = (
    <Button variant="secondary" onClick={onShowNewQr} disabled={isIssuingNewQr}>
      {t('showQr.showNewQr')}
    </Button>
  );
  if (qrProblemMessage !== undefined) {
    return (
      <div className="flex flex-col items-start gap-3">
        <CalmErrorMessage message={qrProblemMessage} />
        {showNewQrButton}
      </div>
    );
  }
  if (isQrLoading || customerQr === undefined) {
    return (
      <div className="rounded-card bg-white p-6">
        <LoadingSkeleton accessibleLabel={t('showQr.issuingQr')} />
      </div>
    );
  }
  if (isQrExpired) {
    return (
      <div className="flex flex-col items-start gap-3 rounded-card bg-white p-6">
        <p role="status" className="text-body text-deep-navy">
          {t('showQr.qrExpired')}
        </p>
        {showNewQrButton}
      </div>
    );
  }
  return (
    <QrPanel
      value={customerQr.customerUrl}
      accessibleLabel={t('showQr.qrAccessibleLabel', { code: sessionCode })}
      caption={t('showQr.qrCaption')}
      stackedSize="fitsPhone"
    />
  );
}
