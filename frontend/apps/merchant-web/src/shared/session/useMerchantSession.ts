import { useContext } from 'react';

import { MerchantSessionContext, type MerchantSessionContextValue } from './merchantSessionContext';

// Gives the paired session and the sign-in and sign-out actions; must be inside MerchantSessionProvider.
export function useMerchantSession(): MerchantSessionContextValue {
  const contextValue = useContext(MerchantSessionContext);
  if (contextValue === undefined) {
    throw new Error('useMerchantSession must be used inside MerchantSessionProvider');
  }
  return contextValue;
}
