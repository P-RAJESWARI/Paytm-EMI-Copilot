import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { installFakeMicrophone, removeFakeMicrophone } from '../../../testing/fakeMicrophone';
import { useVoiceRecorder } from './useVoiceRecorder';

afterEach(() => {
  removeFakeMicrophone();
});

describe('useVoiceRecorder', () => {
  it('is unsupported when the browser cannot record', () => {
    const { result } = renderHook(() => useVoiceRecorder({ onRecorded: vi.fn() }));

    expect(result.current.status).toBe('unsupported');
    act(() => {
      result.current.startRecording();
    });
    expect(result.current.status).toBe('unsupported');
  });

  it('says permission was denied when the customer refuses the microphone', async () => {
    installFakeMicrophone(new DOMException('Permission denied', 'NotAllowedError'));
    const onRecorded = vi.fn();
    const { result } = renderHook(() => useVoiceRecorder({ onRecorded }));

    act(() => {
      result.current.startRecording();
    });

    await waitFor(() => {
      expect(result.current.status).toBe('permissionDenied');
    });
    expect(onRecorded).not.toHaveBeenCalled();
  });

  it('fails quietly when the microphone cannot open for another reason', async () => {
    installFakeMicrophone(new DOMException('No device', 'NotFoundError'));
    const { result } = renderHook(() => useVoiceRecorder({ onRecorded: vi.fn() }));

    act(() => {
      result.current.startRecording();
    });

    await waitFor(() => {
      expect(result.current.status).toBe('failed');
    });
  });

  it('records, hands over one clip on stop, releases the microphone and goes idle', async () => {
    const microphone = installFakeMicrophone();
    const onRecorded = vi.fn<(audio: Blob) => Promise<void>>(() => Promise.resolve());
    const { result } = renderHook(() => useVoiceRecorder({ onRecorded }));

    act(() => {
      result.current.startRecording();
    });
    await waitFor(() => {
      expect(result.current.status).toBe('recording');
    });
    act(() => {
      result.current.stopRecording();
    });

    await waitFor(() => {
      expect(result.current.status).toBe('idle');
    });
    expect(onRecorded).toHaveBeenCalledTimes(1);
    expect(onRecorded.mock.calls[0]?.[0]).toBeInstanceOf(Blob);
    expect(microphone.stoppedTrackCount()).toBe(1);
  });

  it('stops by itself after the maximum duration', async () => {
    installFakeMicrophone();
    const onRecorded = vi.fn(() => Promise.resolve());
    const { result } = renderHook(() =>
      useVoiceRecorder({ onRecorded, maximumDurationInMilliseconds: 5 }),
    );

    act(() => {
      result.current.startRecording();
    });

    await waitFor(() => {
      expect(onRecorded).toHaveBeenCalledTimes(1);
    });
  });

  it('is failed when the upload of the clip fails', async () => {
    installFakeMicrophone();
    const { result } = renderHook(() =>
      useVoiceRecorder({ onRecorded: () => Promise.reject(new Error('upload failed')) }),
    );

    act(() => {
      result.current.startRecording();
    });
    await waitFor(() => {
      expect(result.current.status).toBe('recording');
    });
    act(() => {
      result.current.stopRecording();
    });

    await waitFor(() => {
      expect(result.current.status).toBe('failed');
    });
  });

  it('releases the microphone without uploading when the screen closes mid-recording', async () => {
    const microphone = installFakeMicrophone();
    const onRecorded = vi.fn(() => Promise.resolve());
    const { result, unmount } = renderHook(() => useVoiceRecorder({ onRecorded }));
    act(() => {
      result.current.startRecording();
    });
    await waitFor(() => {
      expect(result.current.status).toBe('recording');
    });

    unmount();

    expect(microphone.stoppedTrackCount()).toBe(1);
    expect(onRecorded).not.toHaveBeenCalled();
  });
});
