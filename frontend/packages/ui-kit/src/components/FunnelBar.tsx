/** `success` colours the final (paid) stage green, as on M5. */
export type FunnelBarTone = 'default' | 'success';

export interface FunnelBarProps {
  /** Translated stage name, for example "Saw the plans". */
  label: string;
  /** The count as shown, already formatted or translated (for example "88" or "fewer than 5"). */
  valueText: string;
  /** The count drawn as the bar, from the API. */
  value: number;
  /** The count drawn as a full bar, usually the first stage. */
  maximumValue: number;
  tone?: FunnelBarTone | undefined;
}

const FULL_BAR_PERCENT = 100;

// Turns a count into a bar width; purely visual scaling, clamped to 0..100%.
function toBarWidthPercent(value: number, maximumValue: number): number {
  if (maximumValue <= 0 || value <= 0) return 0;
  return Math.min(FULL_BAR_PERCENT, (value / maximumValue) * FULL_BAR_PERCENT);
}

// One funnel row: stage name, a decorative bar and the count as text.
export function FunnelBar({
  label,
  valueText,
  value,
  maximumValue,
  tone = 'default',
}: FunnelBarProps) {
  const barWidthPercent = toBarWidthPercent(value, maximumValue);
  return (
    <div className="grid min-h-8 grid-cols-[minmax(0,8rem)_minmax(0,1fr)_auto] items-center gap-3">
      <span className="text-label font-normal">{label}</span>
      <span aria-hidden="true" className="block h-5 rounded-input bg-light-blue">
        <span
          data-testid="funnel-bar-fill"
          className={`block h-5 rounded-input ${tone === 'success' ? 'bg-green' : 'bg-navy'}`}
          style={{ width: `${barWidthPercent}%` }}
        />
      </span>
      <span className="text-right text-body font-bold tabular-nums text-navy">{valueText}</span>
    </div>
  );
}
