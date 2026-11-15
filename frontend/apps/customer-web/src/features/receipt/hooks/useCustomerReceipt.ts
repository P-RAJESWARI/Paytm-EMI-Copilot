import { useQuery } from '@tanstack/react-query';

import { customerQueryKeys, useCustomerFlowApi, type ReceiptStatus } from '../../customer-flow';

/** How often C10 asks again while the shop is still taking the payment. */
export const RECEIPT_POLL_INTERVAL_IN_MILLISECONDS = 5000;

/** Statuses that can still change on the shop's side, so C10 keeps asking. */
const STATUSES_STILL_CHANGING: ReadonlySet<ReceiptStatus> = new Set([
  'READY_TO_PAY',
  'PAYMENT_PENDING',
]);

// Fetches the receipt and keeps polling while the payment is ready or pending; the status is the
// server's, confirmed with Paytm on its side, never trusted from this phone.
export function useCustomerReceipt() {
  const customerFlowApi = useCustomerFlowApi();
  return useQuery({
    queryKey: customerQueryKeys.receipt(),
    queryFn: () => customerFlowApi.getReceipt(),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status !== undefined && STATUSES_STILL_CHANGING.has(status)
        ? RECEIPT_POLL_INTERVAL_IN_MILLISECONDS
        : false;
    },
  });
}
