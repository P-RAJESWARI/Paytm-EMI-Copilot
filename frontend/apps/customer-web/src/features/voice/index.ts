// Public API of the voice feature: the microphone row and the hooks that record and transcribe
// one short clip (C2 budget and C8 teach-back). Audio is never stored.
export { VoiceInputRow } from './components/VoiceInputRow';
export { useVoiceInput } from './hooks/useVoiceInput';
export {
  MAXIMUM_RECORDING_DURATION_IN_MILLISECONDS,
  useVoiceRecorder,
} from './hooks/useVoiceRecorder';
export type { VoiceRecorder } from './hooks/useVoiceRecorder';
export type { VoiceRecorderStatus } from './model/voiceRecorderStatus';
