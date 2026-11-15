import { useTranslation } from 'react-i18next';

import type { AudioPlaybackStatus } from '../hooks/useAudioPlayback';

export interface ListenControlProps {
  status: Exclude<AudioPlaybackStatus, 'unavailable'>;
  onTogglePlayback: () => void;
}

// C7's orange "Listen to this" / "Playing. Tap to pause." control. Every number it speaks is
// also on screen in the text and the highlighted chips.
export function ListenControl({ status, onTogglePlayback }: ListenControlProps) {
  const { t } = useTranslation();
  const isPlaying = status === 'playing';
  const label =
    status === 'loading'
      ? t('explanation.preparingAudio')
      : isPlaying
        ? t('explanation.pause')
        : t('explanation.listen');
  return (
    <div className="flex items-center gap-3 rounded-card bg-white px-3 py-2">
      <button
        type="button"
        aria-label={label}
        onClick={onTogglePlayback}
        disabled={status === 'loading'}
        className="flex size-touch-target-primary shrink-0 items-center justify-center rounded-full bg-orange text-deep-navy disabled:opacity-60"
      >
        {isPlaying ? (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <rect x="6" y="5" width="4" height="14" rx="1" />
            <rect x="14" y="5" width="4" height="14" rx="1" />
          </svg>
        ) : (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M8 5.5v13l11-6.5z" />
          </svg>
        )}
      </button>
      <p aria-hidden="true" className="text-body font-semibold text-deep-navy">
        {label}
      </p>
    </div>
  );
}
