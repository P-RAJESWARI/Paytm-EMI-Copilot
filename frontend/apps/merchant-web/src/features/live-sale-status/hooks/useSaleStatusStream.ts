import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { SALE_QUERY_KEY_ROOT } from '../../../shared/api/saleQueryKeys';
import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import { useMerchantSession } from '../../../shared/session/useMerchantSession';
import { applyLiveStatusEvent } from '../model/applyLiveStatusEvent';
import { SaleStatusStreamFollower } from '../model/SaleStatusStreamFollower';

// Follows the live stream while a merchant is signed in: applies its events, catches up after a
// recovery, signs out on 401 and says whether polling is needed; stops on unmount or sign-out.
export function useSaleStatusStream(): boolean {
  const { fetchFunction, baseUrl } = useMerchantApi();
  const { session, signOut } = useMerchantSession();
  const queryClient = useQueryClient();
  const accessToken = session?.accessToken;
  const [isPolling, setIsPolling] = useState(false);

  useEffect(() => {
    if (accessToken === undefined) return undefined;
    const follower = new SaleStatusStreamFollower(
      { fetchFunction, baseUrl, accessToken },
      {
        onEvent: (event) => {
          applyLiveStatusEvent(queryClient, event);
        },
        // Events sent while disconnected are lost, so read the sales again after any recovery.
        onRecovered: () => void queryClient.invalidateQueries({ queryKey: [SALE_QUERY_KEY_ROOT] }),
        onPollingChange: setIsPolling,
        onSignedOut: signOut,
      },
    );
    follower.start();
    return () => {
      follower.stop();
      setIsPolling(false);
    };
  }, [accessToken, baseUrl, fetchFunction, queryClient, signOut]);

  return isPolling;
}
