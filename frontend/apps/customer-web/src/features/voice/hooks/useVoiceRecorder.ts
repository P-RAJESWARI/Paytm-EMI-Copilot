import { useCallback, useEffect, useRef, useState } from 'react';

import type { VoiceRecorderStatus } from '../model/voiceRecorderStatus';

/** A recording stops by itself after 15 seconds: a budget or a short answer never needs more. */
export const MAXIMUM_RECORDING_DURATION_IN_MILLISECONDS = 15_000;

export interface UseVoiceRecorderOptions {
  /** Receives the finished recording once; the hook keeps no copy after this resolves. */
  onRecorded: (audio: Blob) => Promise<void>;
  maximumDurationInMilliseconds?: number | undefined;
}

export interface VoiceRecorder {
  status: VoiceRecorderStatus;
  startRecording: () => void;
  stopRecording: () => void;
}

/** The live recording: the recorder, its microphone stream and the auto-stop timer. */
interface ActiveRecording {
  mediaRecorder: MediaRecorder;
  mediaStream: MediaStream;
  autoStopTimer: ReturnType<typeof setTimeout>;
}

// True when this browser can record from the microphone at all.
function canRecordAudio(): boolean {
  return (
    typeof window.MediaRecorder === 'function' &&
    'mediaDevices' in navigator &&
    typeof navigator.mediaDevices.getUserMedia === 'function'
  );
}

// True when the browser (or the customer) refused the microphone.
function isPermissionRefusal(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    (error.name === 'NotAllowedError' || error.name === 'SecurityError')
  );
}

// Stops every track so the phone's microphone indicator turns off straight away.
function releaseMicrophone(mediaStream: MediaStream): void {
  for (const track of mediaStream.getTracks()) track.stop();
}

// Records one short clip with MediaRecorder: tap to start, tap to stop (or 15 s), then hands the
// clip to onRecorded. Audio is never stored: the clip is dropped once the upload settles.
export function useVoiceRecorder({
  onRecorded,
  maximumDurationInMilliseconds = MAXIMUM_RECORDING_DURATION_IN_MILLISECONDS,
}: UseVoiceRecorderOptions): VoiceRecorder {
  const [status, setStatus] = useState<VoiceRecorderStatus>(() =>
    canRecordAudio() ? 'idle' : 'unsupported',
  );
  const activeRecordingRef = useRef<ActiveRecording | undefined>(undefined);
  const isMountedRef = useRef(true);
  const onRecordedRef = useRef(onRecorded);
  // Read through a function so each check sees the latest value after an await.
  const isMounted = useCallback(() => isMountedRef.current, []);

  // Keeps the latest onRecorded for a recording that started before a re-render.
  useEffect(() => {
    onRecordedRef.current = onRecorded;
  }, [onRecorded]);

  // Uploads the finished clip and settles the status; nothing happens after unmount.
  const handleRecordingFinished = useCallback(
    async (audio: Blob) => {
      if (!isMounted()) return;
      setStatus('uploading');
      try {
        await onRecordedRef.current(audio);
        if (isMounted()) setStatus('idle');
      } catch {
        if (isMounted()) setStatus('failed');
      }
    },
    [isMounted],
  );

  const stopRecording = useCallback(() => {
    const activeRecording = activeRecordingRef.current;
    if (activeRecording === undefined) return;
    activeRecordingRef.current = undefined;
    clearTimeout(activeRecording.autoStopTimer);
    if (activeRecording.mediaRecorder.state !== 'inactive') activeRecording.mediaRecorder.stop();
    releaseMicrophone(activeRecording.mediaStream);
  }, []);

  const startRecording = useCallback(() => {
    if (!canRecordAudio()) {
      setStatus('unsupported');
      return;
    }
    if (activeRecordingRef.current !== undefined) return;
    void (async () => {
      let mediaStream: MediaStream;
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (error) {
        if (isMounted()) setStatus(isPermissionRefusal(error) ? 'permissionDenied' : 'failed');
        return;
      }
      if (!isMounted()) {
        releaseMicrophone(mediaStream);
        return;
      }
      const mediaRecorder = new MediaRecorder(mediaStream);
      let recordedChunks: Blob[] = [];
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordedChunks.push(event.data);
      };
      mediaRecorder.onstop = () => {
        const audio = new Blob(recordedChunks, { type: mediaRecorder.mimeType });
        recordedChunks = [];
        void handleRecordingFinished(audio);
      };
      const autoStopTimer = setTimeout(stopRecording, maximumDurationInMilliseconds);
      activeRecordingRef.current = { mediaRecorder, mediaStream, autoStopTimer };
      mediaRecorder.start();
      setStatus('recording');
    })();
  }, [handleRecordingFinished, isMounted, maximumDurationInMilliseconds, stopRecording]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      stopRecording();
    };
  }, [stopRecording]);

  return { status, startRecording, stopRecording };
}
