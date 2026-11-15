import { useTranslation } from 'react-i18next';

import { hasVoiceFailed, type VoiceRecorderStatus } from '../model/voiceRecorderStatus';
import { MicrophoneButton } from './MicrophoneButton';

export interface VoiceInputRowProps {
  status: VoiceRecorderStatus;
  /** Translated invitation from the mockup, for example "Tap and say the amount". */
  startLabel: string;
  /** Translated quiet line shown when voice did not work, for example "Please type the amount". */
  typeInsteadMessage: string;
  onStartRecording: () => void;
  onStopRecording: () => void;
}

// The microphone with its words beside it and, when voice did not work, one quiet slate line
// asking to type instead (no banner, no alert: typing always works).
export function VoiceInputRow(props: VoiceInputRowProps) {
  const { t } = useTranslation();
  const isRecording = props.status === 'recording';
  const isUploading = props.status === 'uploading';
  const visibleLabel = isRecording
    ? t('voice.tapToStop')
    : isUploading
      ? t('voice.uploading')
      : props.startLabel;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <MicrophoneButton
          accessibleLabel={visibleLabel}
          isRecording={isRecording}
          isDisabled={isUploading}
          onPress={isRecording ? props.onStopRecording : props.onStartRecording}
        />
        <p aria-hidden="true" className="text-body text-deep-navy">
          {visibleLabel}
        </p>
      </div>
      <p aria-live="polite" className="text-body text-slate">
        {hasVoiceFailed(props.status) ? props.typeInsteadMessage : null}
      </p>
    </div>
  );
}
