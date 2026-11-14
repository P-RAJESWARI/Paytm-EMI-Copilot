import type { BackendApiClient } from '@emi-copilot/api-client';
import { createContext } from 'react';

/** A fetch that takes a ready Request, as the generated client and the event stream use it. */
export type FetchFunction = (request: Request) => Promise<Response>;

export interface MerchantApiContextValue {
  apiClient: BackendApiClient;
  /** The same fetch the client uses, for the live event stream that the client cannot read. */
  fetchFunction: FetchFunction;
  /** The API origin, so the event stream URL matches the client's. */
  baseUrl: string;
}

export const MerchantApiContext = createContext<MerchantApiContextValue | undefined>(undefined);
