import { Button } from '@emi-copilot/ui-kit';

export interface CalmErrorMessageProps {
  /** The translated, calm explanation; never the server's English detail. */
  message: string;
  /** Translated label of the retry button; no button without it. */
  retryLabel?: string | undefined;
  onRetry?: (() => void) | undefined;
}

// A quiet error block with an optional retry; no red banner, no blame (DESIGN_SPEC section 7).
export function CalmErrorMessage({ message, retryLabel, onRetry }: CalmErrorMessageProps) {
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-card bg-grey-tint p-4">
      <p className="text-body text-deep-navy">{message}</p>
      {retryLabel === undefined || onRetry === undefined ? null : (
        <Button variant="secondary" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
