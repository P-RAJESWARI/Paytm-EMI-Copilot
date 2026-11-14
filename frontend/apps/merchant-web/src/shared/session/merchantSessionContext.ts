import type { ApiSchemas } from '@emi-copilot/api-client';
import { createContext } from 'react';

export type MerchantProfile = ApiSchemas['MerchantProfileResponse'];

/** What pairing gives the tablet: the bearer token (memory only) and the shop it belongs to. */
export interface MerchantSession {
  accessToken: string;
  merchant: MerchantProfile;
}

export interface MerchantSessionContextValue {
  session: MerchantSession | undefined;
  signIn: (session: MerchantSession) => void;
  signOut: () => void;
  /** Reads the current token at call time, for request middleware that outlives a render. */
  getAccessToken: () => string | undefined;
}

export const MerchantSessionContext = createContext<MerchantSessionContextValue | undefined>(
  undefined,
);
