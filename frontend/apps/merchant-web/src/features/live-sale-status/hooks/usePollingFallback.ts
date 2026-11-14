import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { SALE_QUERY_KEY_ROOT } from '../../../shared/api/saleQueryKeys';
import { POLLING_INTERVAL_IN_MILLISECONDS } from '../model/liveStatusTiming';

// While the stream is down, reads every open sale screen again every five seconds.
export function usePollingFallback(isPolling: boolean): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!isPolling) return undefined;
    const pollingTimer = setInterval(() => {
      void queryClient.invalidateQueries({ queryKey: [SALE_QUERY_KEY_ROOT] });
    }, POLLING_INTERVAL_IN_MILLISECONDS);
    return () => {
      clearInterval(pollingTimer);
    };
  }, [isPolling, queryClient]);
}
