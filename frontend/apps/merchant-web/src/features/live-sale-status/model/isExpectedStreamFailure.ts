import {
  LiveStatusStreamNetworkError,
  LiveStatusStreamUnavailableError,
} from '../api/openSaleStatusStream';
import { LiveStatusStreamReadError } from './readServerSentEvents';

// True for the failures a live stream is expected to meet (stopped on purpose, aborted, network
// down, no stream opened, connection dropped mid-read); anything else is a bug worth reporting.
export function isExpectedStreamFailure(error: unknown, signal: AbortSignal): boolean {
  if (signal.aborted) return true;
  const isAbortError =
    (error instanceof DOMException || error instanceof Error) && error.name === 'AbortError';
  if (isAbortError) return true;
  return (
    error instanceof LiveStatusStreamNetworkError ||
    error instanceof LiveStatusStreamUnavailableError ||
    error instanceof LiveStatusStreamReadError
  );
}
