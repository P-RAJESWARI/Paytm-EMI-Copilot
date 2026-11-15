import { useMutation } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';

import { useCustomerFlowApi } from '../../customer-flow';

/** Where the Listen control is; `unavailable` hides it quietly (no banner, no alert). */
export type AudioPlaybackStatus = 'idle' | 'loading' | 'playing' | 'paused' | 'unavailable';

export interface AudioPlayback {
  status: AudioPlaybackStatus;
  togglePlayback: () => void;
}

/** The audio element and the object URL it plays, released together. */
interface LoadedAudio {
  audioElement: HTMLAudioElement;
  objectUrl: string;
}

// Plays the spoken explanation: the first tap fetches the audio (synthesis), makes an object URL
// and plays it; later taps pause and resume. The URL is revoked when playback ends, the
// explanation changes or the screen closes. Any failure hides the control quietly.
export function useAudioPlayback(explanationId: string): AudioPlayback {
  const customerFlowApi = useCustomerFlowApi();
  const synthesis = useMutation({
    mutationFn: (id: string) => customerFlowApi.synthesiseExplanation(id),
  });
  const [status, setStatus] = useState<AudioPlaybackStatus>('idle');
  const loadedAudioRef = useRef<LoadedAudio | undefined>(undefined);

  const releaseAudio = useCallback(() => {
    const loadedAudio = loadedAudioRef.current;
    if (loadedAudio === undefined) return;
    loadedAudioRef.current = undefined;
    loadedAudio.audioElement.pause();
    loadedAudio.audioElement.onended = null;
    URL.revokeObjectURL(loadedAudio.objectUrl);
  }, []);

  // Releases the audio when the screen closes; a new explanation remounts this (keyed by id).
  useEffect(() => releaseAudio, [releaseAudio]);

  // Starts (or resumes) playback; a refused play() releases the audio and hides the control.
  const playAudio = useCallback(
    async (audioElement: HTMLAudioElement) => {
      try {
        await audioElement.play();
        setStatus('playing');
      } catch {
        releaseAudio();
        setStatus('unavailable');
      }
    },
    [releaseAudio],
  );

  // Fetches the audio once, then plays it until it ends (which releases it).
  const loadAndPlay = useCallback(async () => {
    setStatus('loading');
    try {
      const audioBlob = await synthesis.mutateAsync(explanationId);
      const objectUrl = URL.createObjectURL(audioBlob);
      const audioElement = new Audio(objectUrl);
      audioElement.onended = () => {
        releaseAudio();
        setStatus('idle');
      };
      loadedAudioRef.current = { audioElement, objectUrl };
      await playAudio(audioElement);
    } catch {
      releaseAudio();
      setStatus('unavailable');
    }
  }, [explanationId, playAudio, releaseAudio, synthesis]);

  const togglePlayback = useCallback(() => {
    const loadedAudio = loadedAudioRef.current;
    if (status === 'playing' && loadedAudio !== undefined) {
      loadedAudio.audioElement.pause();
      setStatus('paused');
    } else if (status === 'paused' && loadedAudio !== undefined) {
      void playAudio(loadedAudio.audioElement);
    } else if (status === 'idle') {
      void loadAndPlay();
    }
  }, [loadAndPlay, playAudio, status]);

  return { status, togglePlayback };
}
