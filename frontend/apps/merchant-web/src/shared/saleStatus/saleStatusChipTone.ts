import type { SaleStatus } from '@emi-copilot/api-client';
import type { StatusChipTone } from '@emi-copilot/ui-kit';

const CHIP_TONE_BY_SALE_STATUS: Record<SaleStatus, StatusChipTone> = {
  CHOOSING: 'choosing',
  READY_TO_PAY: 'ready',
  PAID: 'paid',
  PAYMENT_NOT_COMPLETED: 'notCompleted',
  EXPIRED: 'expired',
};

// Gives the status chip tone (icon and colour) for one of the five merchant-visible statuses.
export function getSaleStatusChipTone(saleStatus: SaleStatus): StatusChipTone {
  return CHIP_TONE_BY_SALE_STATUS[saleStatus];
}
