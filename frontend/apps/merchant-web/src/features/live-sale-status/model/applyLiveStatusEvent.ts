import {
  SALE_STATUS_EVENT_NAME,
  SALE_STATUS_RESYNC_EVENT_NAME,
  parseSaleStatusEventPayload,
} from '@emi-copilot/api-client';
import type { QueryClient } from '@tanstack/react-query';

import {
  COUNTER_SALES_QUERY_KEY,
  SALE_QUERY_KEY_ROOT,
  buildSaleQueryKeyPrefix,
} from '../../../shared/api/saleQueryKeys';
import type { ServerSentEvent } from './ServerSentEventParser';

// Refreshes what one stream event touches: a status change refreshes that sale and the
// counter list; a resync refreshes every open sale screen.
export function applyLiveStatusEvent(queryClient: QueryClient, event: ServerSentEvent): void {
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
