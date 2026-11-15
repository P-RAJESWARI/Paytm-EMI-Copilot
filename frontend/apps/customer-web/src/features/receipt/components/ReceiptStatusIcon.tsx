import type { ReceiptStatus } from '../../customer-flow';

export interface ReceiptStatusIconProps {
  status: ReceiptStatus;
}

const ICON_PATHS_BY_STATUS: Record<ReceiptStatus, readonly string[]> = {
  // An arrow leaving a box: the payment continues on Paytm, with the shop.
  READY_TO_PAY: [
    'M14 4h6v6',
    'M20 4l-9 9',
    'M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5',
  ],
  // A tick: confirmed.
  PAID: ['M5 12.5l4.5 4.5L19 7.5'],
  // A clock: waiting.
  PAYMENT_PENDING: ['M12 3a9 9 0 1 1 0 18a9 9 0 0 1 0-18z', 'M12 7v5l3 2'],
  // An "i": calm, never a cross that reads as "declined".
  PAYMENT_NOT_COMPLETED: ['M12 3a9 9 0 1 1 0 18a9 9 0 0 1 0-18z', 'M12 11v5', 'M12 8v.01'],
};

const CIRCLE_CLASS_NAME_BY_STATUS: Record<ReceiptStatus, string> = {
  READY_TO_PAY: 'bg-cyan-tint text-navy',
  PAID: 'bg-comfortable-tint text-comfortable-text',
  PAYMENT_PENDING: 'bg-stretching-tint text-stretching-text',
  PAYMENT_NOT_COMPLETED: 'bg-grey-tint text-deep-navy',
};

// The large decorative C10 status icon in its tinted circle; the title beside it carries the meaning.
export function ReceiptStatusIcon({ status }: ReceiptStatusIconProps) {
  return (
    <span
      className={`flex h-18 w-18 items-center justify-center rounded-pill ${CIRCLE_CLASS_NAME_BY_STATUS[status]}`}
    >
      <svg
        width="34"
        height="34"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        focusable="false"
        data-receipt-icon={status}
      >
        {ICON_PATHS_BY_STATUS[status].map((pathData) => (
          <path key={pathData} d={pathData} />
        ))}
      </svg>
    </span>
  );
}
