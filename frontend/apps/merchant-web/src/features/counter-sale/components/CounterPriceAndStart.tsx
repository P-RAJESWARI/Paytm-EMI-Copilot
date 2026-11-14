import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { Button } from '@emi-copilot/ui-kit';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import type { CatalogueProduct } from '../api/counterSaleApi';

export interface CounterPriceAndStartProps {
  selectedProduct: CatalogueProduct | undefined;
  onShowQr: () => void;
  isStarting: boolean;
  /** Translated, calm message when starting the sale failed. */
  problemMessage?: string | undefined;
}

// The read-only price at the counter (the list price, plan Q20) and "Show QR to customer".
export function CounterPriceAndStart({
  selectedProduct,
  onShowQr,
  isStarting,
  problemMessage,
}: CounterPriceAndStartProps) {
  const { t } = useTranslation();
  const priceInputId = useId();
  return (
    <div className="flex flex-col gap-3 rounded-card bg-white p-4 shadow-card">
      {selectedProduct === undefined ? (
        <p className="text-body text-slate">{t('counterSale.pickProductHint')}</p>
      ) : (
        <div className="flex flex-col gap-2">
          <label htmlFor={priceInputId} className="text-label">
            {t('counterSale.priceAtCounterLabel', { productName: selectedProduct.name })}
          </label>
          <input
            id={priceInputId}
            readOnly
            value={formatRupeesFromPaise(selectedProduct.listPriceInPaise)}
            className="min-h-touch-target-primary rounded-input border-2 border-border bg-light-blue px-4 text-title tabular-nums text-deep-navy"
          />
        </div>
      )}
      {problemMessage === undefined ? null : (
        <p role="alert" className="rounded-input bg-grey-tint p-3 text-body text-deep-navy">
          {problemMessage}
        </p>
      )}
      <Button
        size="large"
        isFullWidth
        disabled={selectedProduct === undefined || isStarting}
        onClick={onShowQr}
      >
        {isStarting ? t('counterSale.startingSale') : t('counterSale.showQr')}
      </Button>
    </div>
  );
}
