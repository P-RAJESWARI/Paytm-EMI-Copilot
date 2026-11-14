import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import { createIdempotencyKey } from '../../../shared/api/createIdempotencyKey';
import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import { buildSaleHandoffQueryKey, createSalePaymentLink } from '../api/paymentHandoffApi';

// Makes the sale's payment link. "Send payment link" re-sends the key of a failed attempt, so a
// lost answer never makes a second link; "Try again" after a not-completed payment is a new
// intent with a new key. Either way M4 then reads the hand-off again for the true state.
export function useCreatePaymentLink(saleId: string) {
  const { apiClient } = useMerchantApi();
  const queryClient = useQueryClient();
  const unfinishedIdempotencyKey = useRef<string | undefined>(undefined);
  const createLinkMutation = useMutation({
    mutationFn: (idempotencyKey: string) =>
      createSalePaymentLink(apiClient, saleId, idempotencyKey),
    onSuccess: () => {
      unfinishedIdempotencyKey.current = undefined;
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: buildSaleHandoffQueryKey(saleId) }),
  });

  // Sends the link request; `isNewIntent` starts over with a fresh key.
  function createPaymentLink(isNewIntent: boolean) {
    if (isNewIntent || unfinishedIdempotencyKey.current === undefined) {
      unfinishedIdempotencyKey.current = createIdempotencyKey();
    }
    createLinkMutation.mutate(unfinishedIdempotencyKey.current);
  }

  return {
    createPaymentLink,
    isCreatingLink: createLinkMutation.isPending,
    createLinkError: createLinkMutation.error,
  };
}
