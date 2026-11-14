import { formatRupeesFromPaise, formatRupeesWithPaiseFromPaise } from '@emi-copilot/shared-i18n';

const PAISE_PER_RUPEE = 100;

// Gives a price, extra, total or card-machine amount exactly: "₹22,000" for whole rupees and
// "₹124.95" with paise, so the merchant never keys in a rounded figure. Monthly amounts keep the
// design's whole-rupee display (ADR 0001) and do not use this.
export function formatExactRupeesFromPaise(amountInPaise: number): string {
  return amountInPaise % PAISE_PER_RUPEE === 0
    ? formatRupeesFromPaise(amountInPaise)
    : formatRupeesWithPaiseFromPaise(amountInPaise);
}
