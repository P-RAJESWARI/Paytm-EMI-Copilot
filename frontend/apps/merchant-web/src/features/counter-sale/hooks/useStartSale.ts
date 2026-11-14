import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import { createIdempotencyKey } from '../../../shared/api/createIdempotencyKey';
import { COUNTER_SALES_QUERY_KEY } from '../../../shared/api/saleQueryKeys';
import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import {
  buildCustomerQrQueryKey,
  buildSaleDetailQueryKey,
  startSale,
  type SaleDetail,
} from '../api/counterSaleApi';

/** One "Show QR to customer" intent: the product and the key every retry of it re-sends. */
interface StartSaleIntent {
  productId: string;
  idempotencyKey: string;
}

// Starts a sale for a product. A retry of the same product after a failure re-sends the same
// Idempotency-Key, so a lost answer never creates a second sale. The QR code goes into the
// in-memory cache only (never router state or storage).
export function useStartSale() {
  const { apiClient } = useMerchantApi();
  const queryClient = useQueryClient();
  const pendingIntent = useRef<StartSaleIntent | undefined>(undefined);
  const startSaleMutation = useMutation({
    mutationFn: (intent: StartSaleIntent) =>
      startSale(apiClient, intent.productId, intent.idempotencyKey),
    onSuccess: (saleDetail: SaleDetail) => {
      pendingIntent.current = undefined;
      if (saleDetail.qr !== null) {
        queryClient.setQueryData(buildCustomerQrQueryKey(saleDetail.saleId), saleDetail.qr);
      }
      queryClient.setQueryData(buildSaleDetailQueryKey(saleDetail.saleId), {
        ...saleDetail,
        qr: null,
      });
      void queryClient.invalidateQueries({ queryKey: COUNTER_SALES_QUERY_KEY });
    },
  });

  // Starts (or retries) the sale for one product and calls onStarted with the new sale's id.
  function startSaleForProduct(productId: string, onStarted: (saleId: string) => void) {
    if (pendingIntent.current?.productId !== productId) {
      pendingIntent.current = { productId, idempotencyKey: createIdempotencyKey() };
    }
    startSaleMutation.mutate(pendingIntent.current, {
      onSuccess: (saleDetail) => {
        onStarted(saleDetail.saleId);
      },
    });
  }

  return {
    startSaleForProduct,
    isStarting: startSaleMutation.isPending,
    startError: startSaleMutation.error,
  };
}
