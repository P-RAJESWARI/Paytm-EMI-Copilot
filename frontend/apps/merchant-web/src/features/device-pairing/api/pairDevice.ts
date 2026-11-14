import type { ApiSchemas, BackendApiClient } from '@emi-copilot/api-client';

import { readApiData } from '../../../shared/api/readApiData';

export type PairDeviceRequest = ApiSchemas['PairDeviceRequest'];
export type DevicePairing = ApiSchemas['DevicePairingResponse'];

// Trades the shop ID and pairing PIN for a device token (POST /merchants/pairing).
export function pairDevice(
  apiClient: BackendApiClient,
  pairDeviceRequest: PairDeviceRequest,
): Promise<DevicePairing> {
  return readApiData(apiClient.POST('/api/v1/merchants/pairing', { body: pairDeviceRequest }));
}
