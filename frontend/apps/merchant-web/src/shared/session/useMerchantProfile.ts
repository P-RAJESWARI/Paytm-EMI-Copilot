import { useQuery } from '@tanstack/react-query';

import { readApiData } from '../api/readApiData';
import { useMerchantApi } from '../api/useMerchantApi';
import type { MerchantProfile } from './merchantSessionContext';
import { useMerchantSession } from './useMerchantSession';

export const MERCHANT_PROFILE_QUERY_KEY = ['merchant-profile'] as const;

// Reads the signed-in shop and device (GET /merchants/me), starting from what pairing returned.
export function useMerchantProfile() {
  const { apiClient } = useMerchantApi();
  const { session } = useMerchantSession();
  return useQuery<MerchantProfile>({
    queryKey: MERCHANT_PROFILE_QUERY_KEY,
    queryFn: () => readApiData(apiClient.GET('/api/v1/merchants/me')),
    initialData: () => session?.merchant,
    enabled: session !== undefined,
  });
}
