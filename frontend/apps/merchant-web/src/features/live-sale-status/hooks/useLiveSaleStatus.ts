import { usePollingFallback } from './usePollingFallback';
import { useSaleStatusStream } from './useSaleStatusStream';

// Keeps every sale screen live: follows GET /sales/events with fetch and the Authorization
// header, reconnects with growing waits, polls every 5 s after three failures in a row, signs out
// on 401 and stops on unmount or sign-out.
export function useLiveSaleStatus(): { isPolling: boolean } {
  const isPolling = useSaleStatusStream();
  usePollingFallback(isPolling);
  return { isPolling };
}
