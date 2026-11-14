import { useContext } from 'react';

import { MerchantApiContext, type MerchantApiContextValue } from './merchantApiContext';

// Gives the app's generated API client and fetch; must be inside MerchantApiProvider.
export function useMerchantApi(): MerchantApiContextValue {
  const contextValue = useContext(MerchantApiContext);
  if (contextValue === undefined) {
    throw new Error('useMerchantApi must be used inside MerchantApiProvider');
  }
  return contextValue;
}
