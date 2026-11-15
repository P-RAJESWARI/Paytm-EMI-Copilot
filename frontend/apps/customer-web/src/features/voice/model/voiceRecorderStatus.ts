/** Where one microphone attempt is; the last three mean "type it instead". */
export type VoiceRecorderStatus =
  'idle' | 'recording' | 'uploading' | 'permissionDenied' | 'unsupported' | 'failed';

// True when voice did not work this time, so the screen shows the quiet "type it" line.
export function hasVoiceFailed(status: VoiceRecorderStatus): boolean {
  return status === 'permissionDenied' || status === 'unsupported' || status === 'failed';
}
