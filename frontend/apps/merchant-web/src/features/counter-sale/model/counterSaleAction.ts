import type { SaleStatus } from '@emi-copilot/api-client';

/** What the counter list offers for a sale: take the payment, show the QR again, or nothing. */
export type CounterSaleAction = 'takePayment' | 'showQr' | 'none';

const ACTION_BY_SALE_STATUS: Record<SaleStatus, CounterSaleAction> = {
  CHOOSING: 'showQr',
  READY_TO_PAY: 'takePayment',
  PAYMENT_NOT_COMPLETED: 'takePayment',
  PAID: 'none',
  EXPIRED: 'none',
};

// Gives the counter-list action for a sale status ("Ready to pay" only after consent, spec 7.7).
export function getCounterSaleAction(saleStatus: SaleStatus): CounterSaleAction {
  return ACTION_BY_SALE_STATUS[saleStatus];
}
