export interface LoadingSkeletonProps {
  /** Translated "Loading…" (or more specific), read by screen readers. */
  accessibleLabel: string;
  lineCount?: number | undefined;
}

const DEFAULT_LINE_COUNT = 3;

// Grey placeholder lines shown while a screen's data loads; static, no animation (weak phones).
export function LoadingSkeleton({
  accessibleLabel,
  lineCount = DEFAULT_LINE_COUNT,
}: LoadingSkeletonProps) {
  return (
    <div role="status" aria-label={accessibleLabel} className="flex flex-col gap-3 py-2">
      {Array.from({ length: lineCount }, (_unused, lineIndex) => (
        <span
          key={lineIndex}
          aria-hidden="true"
          className={`block h-4 rounded-input bg-grey-tint ${lineIndex === lineCount - 1 ? 'w-2/3' : 'w-full'}`}
        />
      ))}
    </div>
  );
}
