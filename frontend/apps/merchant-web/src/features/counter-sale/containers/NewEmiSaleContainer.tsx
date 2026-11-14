import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';

import { buildShowQrPath } from '../../../app/merchantPaths';
import { getProblemMessageKey } from '../../../shared/api/problemMessageKey';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import type { CatalogueProduct } from '../api/counterSaleApi';
import { CounterPriceAndStart } from '../components/CounterPriceAndStart';
import { ProductPicker } from '../components/ProductPicker';
import { ProductSearchField } from '../components/ProductSearchField';
import { useProductSearch } from '../hooks/useProductSearch';
import { useStartSale } from '../hooks/useStartSale';

// Container for M2's left column: search, pick a product, then start the sale and open M3.
export function NewEmiSaleContainer() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<CatalogueProduct | undefined>(undefined);
  const { productsQuery, searchedText } = useProductSearch(searchText);
  const { startSaleForProduct, isStarting, startError } = useStartSale();

  // Starts the sale for the chosen product and shows its QR code.
  function handleShowQr() {
    if (selectedProduct === undefined) return;
    startSaleForProduct(selectedProduct.productId, (saleId) => {
      void navigate(buildShowQrPath(saleId));
    });
  }

  let productListContent;
  if (productsQuery.isPending) {
    productListContent = <LoadingSkeleton accessibleLabel={t('counterSale.loadingProducts')} />;
  } else if (productsQuery.isError) {
    productListContent = (
      <CalmErrorMessage
        message={t(getProblemMessageKey(productsQuery.error))}
        retryLabel={t('common.tryAgain')}
        onRetry={() => void productsQuery.refetch()}
      />
    );
  } else if (productsQuery.data.length === 0) {
    productListContent = (
      <p className="rounded-card bg-white p-4 text-body text-slate">
        {searchedText === ''
          ? t('counterSale.noProducts')
          : t('counterSale.noProductsFound', { search: searchedText })}
      </p>
    );
  } else {
    productListContent = (
      <ProductPicker
        products={productsQuery.data}
        selectedProductId={selectedProduct?.productId}
        onSelectProduct={setSelectedProduct}
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <ProductSearchField searchText={searchText} onSearchTextChange={setSearchText} />
      {productListContent}
      <CounterPriceAndStart
        selectedProduct={selectedProduct}
        onShowQr={handleShowQr}
        isStarting={isStarting}
        problemMessage={startError === null ? undefined : t(getProblemMessageKey(startError))}
      />
    </div>
  );
}
