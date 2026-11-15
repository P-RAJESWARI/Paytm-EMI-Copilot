import { vi } from 'vitest';

/** The data and stop events a real MediaRecorder raises, as the hook listens to them. */
type DataAvailableListener = (event: { data: Blob }) => void;

// A stand-in for the browser's MediaRecorder: start records, stop hands over one small clip.
export class FakeMediaRecorder {
  state: 'inactive' | 'recording' = 'inactive';
  readonly mimeType = 'audio/webm';
  ondataavailable: DataAvailableListener | null = null;
  onstop: (() => void) | null = null;

  // Starts "recording" on the given stream.
  start(): void {
    this.state = 'recording';
  }

  // Stops and delivers the clip, as a browser does: one data event, then the stop event.
  stop(): void {
    this.state = 'inactive';
    this.ondataavailable?.({ data: new Blob(['spoken words'], { type: this.mimeType }) });
    this.onstop?.();
  }
}

export interface FakeMicrophone {
  getUserMedia: ReturnType<typeof vi.fn>;
  /** How many microphone tracks were stopped (the phone's mic indicator turned off). */
  stoppedTrackCount: () => number;
}

// Installs a fake microphone and MediaRecorder on the page; pass a failure to refuse access.
// Call removeFakeMicrophone in afterEach.
export function installFakeMicrophone(accessFailure?: Error): FakeMicrophone {
  let stoppedTracks = 0;
  const fakeTrack = {
    stop: () => {
      stoppedTracks += 1;
    },
  };
  const getUserMedia = vi.fn(() =>
    accessFailure === undefined
      ? Promise.resolve({ getTracks: () => [fakeTrack] })
      : Promise.reject(accessFailure),
  );
  vi.stubGlobal('MediaRecorder', FakeMediaRecorder);
  Object.defineProperty(navigator, 'mediaDevices', {
    value: { getUserMedia },
    configurable: true,
  });
  return { getUserMedia, stoppedTrackCount: () => stoppedTracks };
}

// Removes the fake microphone so the next test starts without one.
export function removeFakeMicrophone(): void {
  vi.unstubAllGlobals();
  Reflect.deleteProperty(navigator, 'mediaDevices');
}
