import type { SpeechPurpose, SpeechTranscription } from '../../customer-flow';
import { useSpeechTranscription } from './useSpeechTranscription';
import { useVoiceRecorder, type VoiceRecorder } from './useVoiceRecorder';

// Records a clip and transcribes it for one purpose, then hands the transcription to the screen;
// a failed upload leaves the recorder in its "failed" state so the screen says "type it instead".
export function useVoiceInput(
  purpose: SpeechPurpose,
  onTranscribed: (transcription: SpeechTranscription) => void,
): VoiceRecorder {
  const transcription = useSpeechTranscription(purpose);
  return useVoiceRecorder({
    onRecorded: async (audio) => {
      onTranscribed(await transcription.mutateAsync(audio));
    },
  });
}
