import { StatusIcon } from '../icons/StatusIcon';
import type { StatusChipTone } from './statusChipTone';

export interface StatusChipProps {
  tone: StatusChipTone;
  /** The translated status word, for example "Ready to pay". */
  label: string;
}

const TONE_CLASS_NAMES: Record<StatusChipTone, string> = {
  choosing: 'bg-status-choosing-tint text-status-choosing-text',
  ready: 'bg-status-ready-tint text-status-ready-text',
  paid: 'bg-status-paid-tint text-status-paid-text',
  notCompleted: 'bg-status-not-completed-tint text-status-not-completed-text',
  expired: 'bg-status-expired-tint text-status-expired-text',
  neutral: 'bg-status-neutral-tint text-status-neutral-text',
};

// Shows a sale status as icon and word together, never colour alone.
export function StatusChip({ tone, label }: StatusChipProps) {
  return (
    <span
      className={`inline-flex min-h-8 items-center gap-2 rounded-pill px-3 text-label ${TONE_CLASS_NAMES[tone]}`}
    >
      <StatusIcon tone={tone} />
      {label}
    </span>
  );
}
