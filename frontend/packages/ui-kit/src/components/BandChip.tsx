import { BandIcon } from '../icons/BandIcon';
import type { BandChipTone } from './bandChipTone';

export interface BandChipProps {
  tone: BandChipTone;
  /** The translated band word, for example "Stretching". */
  label: string;
  /** Optional translated text after the word, for example "38.9% of monthly inflow". */
  detail?: string | undefined;
}

const TONE_CLASS_NAMES: Record<BandChipTone, string> = {
  comfortable: 'bg-comfortable-tint text-comfortable-text',
  stretching: 'bg-stretching-tint text-stretching-text',
  risky: 'bg-risky-tint text-risky-text',
};

// Shows a comfort band as icon and word together on its text-safe tint, never colour alone.
export function BandChip({ tone, label, detail }: BandChipProps) {
  return (
    <span
      className={`inline-flex min-h-8 items-center gap-2 rounded-pill px-3 text-label ${TONE_CLASS_NAMES[tone]}`}
    >
      <BandIcon tone={tone} />
      {label}
      {detail === undefined ? null : (
        <>
          {' '}
          <span className="font-normal tabular-nums">{detail}</span>
        </>
      )}
    </span>
  );
}
