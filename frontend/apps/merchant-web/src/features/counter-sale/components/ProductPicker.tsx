import type { TFunction } from 'i18next';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import { formatExactRupeesFromPaise } from '../../../shared/formatting/formatExactRupees';
import type { CatalogueProduct } from '../api/counterSaleApi';

export interface ProductPickerProps {
  products: readonly CatalogueProduct[];
  selectedProductId: string | undefined;
  onSelectProduct: (product: CatalogueProduct) => void;
}

// Says what a product's offers are, from the API counts: "3 EMI plans, 1 with no extra cost".
function describeProductOffers(t: TFunction, product: CatalogueProduct): string {
  if (product.planCount === 0) return t('counterSale.offers.none');
  const planSummary = t('counterSale.offers.planCount', { count: product.planCount });
  if (product.noExtraCostPlanCount === 0) return planSummary;
  return t('counterSale.offers.withNoExtraCost', {
    planSummary,
    count: product.noExtraCostPlanCount,
  });
}

// The product list as one radio group (native radios, so arrow keys work), each row showing the
// offer summary and the list price.
export function ProductPicker({
  products,
  selectedProductId,
  onSelectProduct,
}: ProductPickerProps) {
  const { t } = useTranslation();
  const groupName = useId();
  return (
    <fieldset className="m-0 flex min-w-0 flex-col gap-2 border-0 p-0">
      <legend className="sr-only">{t('counterSale.productsLabel')}</legend>
      {products.map((product) => {
        const isSelected = product.productId === selectedProductId;
        return (
          <label
            key={product.productId}
            className={`flex min-h-touch-target cursor-pointer items-center justify-between gap-3 rounded-card border-2 px-4 py-3 has-[:focus-visible]:outline-3 has-[:focus-visible]:outline-navy ${
              isSelected ? 'border-cyan bg-cyan-tint' : 'border-white bg-white'
            }`}
          >
            <input
              type="radio"
              name={groupName}
              value={product.productId}
              checked={isSelected}
              onChange={() => {
                onSelectProduct(product);
              }}
              className="sr-only"
            />
            <span className="flex flex-col gap-1">
              <span className="text-body font-bold text-deep-navy">{product.name}</span>
              <span className="text-label font-normal text-slate">
                {describeProductOffers(t, product)}
              </span>
            </span>
            <span className="text-lead font-bold tabular-nums text-navy">
              {formatExactRupeesFromPaise(product.listPriceInPaise)}
            </span>
          </label>
        );
      })}
    </fieldset>
  );
}
