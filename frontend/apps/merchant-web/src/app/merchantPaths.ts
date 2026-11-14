/** Every merchant route path in one place, so links and routes never drift apart. */
export const MERCHANT_PATHS = {
  pairing: '/pair',
  newEmiSale: '/sale',
  salesReport: '/report',
  weeklyMessage: '/report/weekly-message',
  showQrPattern: '/sale/:saleId/qr',
  takePaymentPattern: '/sale/:saleId/handoff',
} as const;

// Gives the M3 path that shows one sale's QR code.
export function buildShowQrPath(saleId: string): string {
  return `/sale/${encodeURIComponent(saleId)}/qr`;
}

// Gives the M4 path that takes payment for one sale.
export function buildTakePaymentPath(saleId: string): string {
  return `/sale/${encodeURIComponent(saleId)}/handoff`;
}
