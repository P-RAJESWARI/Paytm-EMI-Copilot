import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import {
  buildSaleHandoffQueryKey,
  checkSalePaymentStatus,
  type SaleHandoff,
} from '../api/paymentHandoffApi';

// "Refresh status": asks the server to check the payment with the gateway, shows its answer at
// once and then reads the whole hand-off again. A client never decides that a payment succeeded.
export function useRefreshPaymentStatus(saleId: string) {
  const { apiClient } = useMerchantApi();
  const queryClient = useQueryClient();
  const handoffQueryKey = buildSaleHandoffQueryKey(saleId);
  return useMutation({
    mutationFn: () => checkSalePaymentStatus(apiClient, saleId),
    onSuccess: (salePaymentStatus) => {
      queryClient.setQueryData<SaleHandoff>(handoffQueryKey, (handoff) =>
        handoff === undefined ? undefined : { ...handoff, ...salePaymentStatus },
      );
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: handoffQueryKey }),
  });
}
