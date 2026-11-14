import {
  SALE_STATUS_EVENT_NAME,
  SALE_STATUS_EVENTS_PATH,
  SALE_STATUS_RESYNC_EVENT_NAME,
  parseSaleStatusEventPayload,
} from '@emi-copilot/api-client';
import { useQueryClient, type QueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import {
  COUNTER_SALES_QUERY_KEY,
  SALE_QUERY_KEY_ROOT,
  buildSaleQueryKeyPrefix,
} from '../../../shared/api/saleQueryKeys';
import { useMerchantSession } from '../../../shared/session/useMerchantSession';
import {
  POLLING_FALLBACK_FAILURE_COUNT,
  POLLING_INTERVAL_IN_MILLISECONDS,
  getReconnectDelayInMilliseconds,
} from '../model/liveStatusTiming';
import { readServerSentEvents } from '../model/readServerSentEvents';
import type { ServerSentEvent } from '../model/ServerSentEventParser';

/** The stream answered, but not with an open event stream. */
class LiveStatusStreamUnavailableError extends Error {}

// Refreshes what one stream event touches: a status change refreshes that sale and the
// counter list; a resync refreshes every open sale screen.
function applyLiveStatusEvent(queryClient: QueryClient, event: ServerSentEvent): void {
  if (event.eventName === SALE_STATUS_RESYNC_EVENT_NAME) {
    void queryClient.invalidateQueries({ queryKey: [SALE_QUERY_KEY_ROOT] });
    return;
  }
  if (event.eventName !== SALE_STATUS_EVENT_NAME) return;
  const payload = parseSaleStatusEventPayload(event.data);
  if (payload === undefined) return;
  void queryClient.invalidateQueries({ queryKey: COUNTER_SALES_QUERY_KEY });
  void queryClient.invalidateQueries({ queryKey: buildSaleQueryKeyPrefix(payload.saleId) });
}

// True for the failures a dropped or refused stream causes; anything else is a bug and is rethrown.
function isConnectionFailure(error: unknown): boolean {
  return (
    error instanceof TypeError ||
    error instanceof DOMException ||
    error instanceof LiveStatusStreamUnavailableError
  );
}

// Keeps every sale screen live: follows GET /sales/events with fetch and the Authorization
// header (the token never goes in a URL), reconnects with growing waits, polls every 5 s after
// three failures in a row, signs out on 401 and stops on unmount or sign-out.
export function useLiveSaleStatus(): { isPolling: boolean } {
  const { fetchFunction, baseUrl } = useMerchantApi();
  const { session, signOut } = useMerchantSession();
  const queryClient = useQueryClient();
  const accessToken = session?.accessToken;
  const [isPolling, setIsPolling] = useState(false);

  useEffect(() => {
    if (accessToken === undefined) return undefined;
    const abortController = new AbortController();
    let consecutiveFailureCount = 0;
    let hasConnectedBefore = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    // Counts a failure, switches polling on after three, and tries again after the backoff.
    function scheduleReconnect() {
      consecutiveFailureCount += 1;
      if (consecutiveFailureCount >= POLLING_FALLBACK_FAILURE_COUNT) setIsPolling(true);
      reconnectTimer = setTimeout(() => {
        void connect();
      }, getReconnectDelayInMilliseconds(consecutiveFailureCount));
    }

    // Opens the stream once and reads it until it ends or fails.
    async function connect() {
      try {
        const response = await fetchFunction(
          new Request(`${baseUrl}${SALE_STATUS_EVENTS_PATH}`, {
            headers: { Authorization: `Bearer ${accessToken ?? ''}`, Accept: 'text/event-stream' },
            cache: 'no-store',
            signal: abortController.signal,
          }),
        );
        if (response.status === 401) {
          signOut();
          return;
        }
        if (!response.ok || response.body === null) throw new LiveStatusStreamUnavailableError();
        // Events sent while disconnected are lost, so read the sales again after any recovery.
        if (hasConnectedBefore || consecutiveFailureCount > 0) {
          void queryClient.invalidateQueries({ queryKey: [SALE_QUERY_KEY_ROOT] });
        }
        consecutiveFailureCount = 0;
        hasConnectedBefore = true;
        setIsPolling(false);
        await readServerSentEvents(response.body, abortController.signal, (event) => {
          applyLiveStatusEvent(queryClient, event);
        });
      } catch (error) {
        if (!isConnectionFailure(error)) throw error;
      }
      if (!abortController.signal.aborted) scheduleReconnect();
    }

    void connect();
    return () => {
      abortController.abort();
      clearTimeout(reconnectTimer);
      setIsPolling(false);
    };
  }, [accessToken, baseUrl, fetchFunction, queryClient, signOut]);

  useEffect(() => {
    if (!isPolling) return undefined;
    const pollingTimer = setInterval(() => {
      void queryClient.invalidateQueries({ queryKey: [SALE_QUERY_KEY_ROOT] });
    }, POLLING_INTERVAL_IN_MILLISECONDS);
    return () => {
      clearInterval(pollingTimer);
    };
  }, [isPolling, queryClient]);

  return { isPolling };
}
