export interface SegmentedControlOption<Value extends string> {
  value: Value;
  label: string;
}

export interface SegmentedControlProps<Value extends string> {
  /** Translated group name, for example "Period". */
  accessibleLabel: string;
  options: readonly SegmentedControlOption<Value>[];
  selectedValue: Value;
  onSelectValue: (value: Value) => void;
}

// A row of pressed-state buttons for one choice, like Today / This week / This month on M5.
export function SegmentedControl<Value extends string>({
  accessibleLabel,
  options,
  selectedValue,
  onSelectValue,
}: SegmentedControlProps<Value>) {
  return (
    <div
      role="group"
      aria-label={accessibleLabel}
      className="inline-flex rounded-input border border-border bg-white p-1"
    >
      {options.map((option) => {
        const isSelected = option.value === selectedValue;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={isSelected}
            onClick={() => {
              onSelectValue(option.value);
            }}
            className={`min-h-touch-target rounded-input px-3 text-label ${
              isSelected ? 'bg-navy text-white' : 'bg-transparent text-navy'
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
