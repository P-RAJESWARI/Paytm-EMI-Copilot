export interface MicrophoneButtonProps {
  /** Translated label read aloud and shown beside the button, for example "Tap and say the amount". */
  accessibleLabel: string;
  isRecording: boolean;
  isDisabled: boolean;
  onPress: () => void;
}

// The round orange voice button (56 px): a microphone to start, a square to stop recording.
export function MicrophoneButton({
  accessibleLabel,
  isRecording,
  isDisabled,
  onPress,
}: MicrophoneButtonProps) {
  return (
    <button
      type="button"
      aria-label={accessibleLabel}
      onClick={onPress}
      disabled={isDisabled}
      className="flex size-touch-target-primary shrink-0 items-center justify-center rounded-full bg-orange text-deep-navy disabled:opacity-60"
    >
      {isRecording ? (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <rect x="6" y="6" width="12" height="12" rx="2" />
        </svg>
      ) : (
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <rect x="9" y="3" width="6" height="11" rx="3" />
          <path d="M5 11a7 7 0 0 0 14 0" />
          <path d="M12 18v3" />
        </svg>
      )}
    </button>
  );
}
