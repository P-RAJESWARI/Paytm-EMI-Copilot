import { useMutation, useQueryClient, type QueryClient } from '@tanstack/react-query';

import { COUNTER_SALES_QUERY_KEY } from '../../../shared/api/saleQueryKeys';
import { useIdempotencyKeyPerIntent } from '../../../shared/api/useIdempotencyKeyPerIntent';
import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import {
  buildCustomerQrQueryKey,
  buildSaleDetailQueryKey,
  startSale,
  type SaleDetail,
} from '../api/counterSaleApi';

/** One "Show QR to customer" request: the product and the Idempotency-Key it is sent with. */
interface StartSaleIntent {
  productId: string;
  idempotencyKey: string;
}

// Puts a started sale in the cache: its QR code in memory only (never router state or storage),
// the sale without the QR, and a fresh counter list.
function storeStartedSale(queryClient: QueryClient, saleDetail: SaleDetail): void {
  if (saleDetail.qr !== null) {
    queryClient.setQueryData(buildCustomerQrQueryKey(saleDetail.saleId), saleDetail.qr);
  }
  queryClient.setQueryData(buildSaleDetailQueryKey(saleDetail.saleId), { ...saleDetail, qr: null });
  void queryClient.invalidateQueries({ queryKey: COUNTER_SALES_QUERY_KEY });
}

// Starts a sale for a product. A retry of the same product re-sends the key only when the last
// answer was lost, so a lost answer never creates a second sale; a definite answer retires the key.
export function useStartSale() {
  const { apiClient } = useMerchantApi();
  const queryClient = useQueryClient();
  const idempotencyKeys = useIdempotencyKeyPerIntent();
  const startSaleMutation = useMutation({
    mutationFn: (intent: StartSaleIntent) =>
      startSale(apiClient, intent.productId, intent.idempotencyKey),
    onSuccess: (saleDetail: SaleDetail) => {
      storeStartedSale(queryClient, saleDetail);
    },
    onSettled: (_saleDetail, error, intent) => {
      idempotencyKeys.settleIdempotencyKey(intent.idempotencyKey, error);
    },
  });

  // Starts (or retries) the sale for one product and calls onStarted with the new sale's id.
  function startSaleForProduct(productId: string, onStarted: (saleId: string) => void) {
    const idempotencyKey = idempotencyKeys.takeIdempotencyKey(productId);
    startSaleMutation.mutate(
      { productId, idempotencyKey },
      {
        onSuccess: (saleDetail) => {
          onStarted(saleDetail.saleId);
        },
      },
    );
  }

  return {
    startSaleForProduct,
    isStarting: startSaleMutation.isPending,
    startError: startSaleMutation.error,
  };
}
