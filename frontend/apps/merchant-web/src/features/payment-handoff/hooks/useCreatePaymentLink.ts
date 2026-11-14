import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useIdempotencyKeyPerIntent } from '../../../shared/api/useIdempotencyKeyPerIntent';
import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import { buildSaleHandoffQueryKey, createSalePaymentLink } from '../api/paymentHandoffApi';

// Makes the sale's payment link. "Send payment link" re-sends the key only when the last answer was
// lost, so it never makes a second link; any definite answer, or "Try again" after a not-completed
// payment, starts a new key. Either way M4 then reads the hand-off again for the true state.
export function useCreatePaymentLink(saleId: string) {
  const { apiClient } = useMerchantApi();
  const queryClient = useQueryClient();
  const idempotencyKeys = useIdempotencyKeyPerIntent();
  const createLinkMutation = useMutation({
    mutationFn: (idempotencyKey: string) =>
      createSalePaymentLink(apiClient, saleId, idempotencyKey),
    onSettled: (_paymentLink, error, idempotencyKey) => {
      idempotencyKeys.settleIdempotencyKey(idempotencyKey, error);
      return queryClient.invalidateQueries({ queryKey: buildSaleHandoffQueryKey(saleId) });
    },
  });

  // Sends the link request; `isNewIntent` starts over with a fresh key.
  function createPaymentLink(isNewIntent: boolean) {
    createLinkMutation.mutate(idempotencyKeys.takeIdempotencyKey(saleId, isNewIntent));
  }

  return {
    createPaymentLink,
    isCreatingLink: createLinkMutation.isPending,
    createLinkError: createLinkMutation.error,
  };
}
