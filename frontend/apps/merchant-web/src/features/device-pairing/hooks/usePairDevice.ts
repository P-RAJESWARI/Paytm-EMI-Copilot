import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useMerchantApi } from '../../../shared/api/useMerchantApi';
import { MERCHANT_PROFILE_QUERY_KEY } from '../../../shared/session/useMerchantProfile';
import { useMerchantSession } from '../../../shared/session/useMerchantSession';
import { pairDevice, type PairDeviceRequest } from '../api/pairDevice';

// Pairs the tablet: on success the token goes into the in-memory session and the shop card is
// filled from the answer, so the shell shows the shop at once.
export function usePairDevice() {
  const { apiClient } = useMerchantApi();
  const { signIn } = useMerchantSession();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (pairDeviceRequest: PairDeviceRequest) => pairDevice(apiClient, pairDeviceRequest),
    onSuccess: (devicePairing) => {
      queryClient.setQueryData(MERCHANT_PROFILE_QUERY_KEY, devicePairing.merchant);
      signIn({ accessToken: devicePairing.accessToken, merchant: devicePairing.merchant });
    },
  });
}
