import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { isSessionLostError } from '../api/customerApiError';

// Calls onSessionLost when any query or mutation fails because the session is gone (a used QR,
// an expired or replaced token), so every screen ends on "ask the shop for a new QR" alike.
export function useSessionLossWatcher(onSessionLost: () => void): void {
  const queryClient = useQueryClient();
  useEffect(() => {
    const stopWatchingQueries = queryClient.getQueryCache().subscribe((event) => {
      if (event.type === 'updated' && event.action.type === 'error') {
        if (isSessionLostError(event.action.error)) onSessionLost();
      }
    });
    const stopWatchingMutations = queryClient.getMutationCache().subscribe((event) => {
      if (event.type === 'updated' && event.action.type === 'error') {
        if (isSessionLostError(event.action.error)) onSessionLost();
      }
    });
    return () => {
      stopWatchingQueries();
      stopWatchingMutations();
    };
  }, [queryClient, onSessionLost]);
}
