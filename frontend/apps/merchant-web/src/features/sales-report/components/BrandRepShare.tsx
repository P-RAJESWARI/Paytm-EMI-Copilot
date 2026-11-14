import { Button } from '@emi-copilot/ui-kit';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import type { CopyState } from '../../../shared/clipboard/useCopyToClipboard';

export interface BrandRepShareProps {
  shareText: string;
  onShare: () => void;
  copyState: CopyState;
}

// "Share with brand rep": copies the summary for the merchant to paste anywhere; nothing is
// sent. Where copying is unavailable, the text appears to select by hand.
export function BrandRepShare({ shareText, onShare, copyState }: BrandRepShareProps) {
  const { t } = useTranslation();
  const fallbackTextId = useId();
  return (
    <div className="flex flex-col items-start gap-2">
      <Button variant="secondary" onClick={onShare}>
        {t('report.share.button')}
      </Button>
      <p role="status" className="text-label font-normal text-slate">
        {copyState === 'copied' ? t('report.share.copied') : null}
      </p>
      {copyState === 'unavailable' ? (
        <div className="flex w-full flex-col gap-1">
          <label htmlFor={fallbackTextId} className="text-label font-normal text-slate">
            {t('report.share.copyByHand')}
          </label>
          <textarea
            id={fallbackTextId}
            readOnly
            value={shareText}
            rows={4}
            className="w-full rounded-input border border-border bg-white p-3 text-label font-normal text-deep-navy"
          />
        </div>
      ) : null}
    </div>
  );
}
