import { useContext } from 'react';

import { CustomerFlowApiContext } from '../api/customerFlowApiContext';
import type { CustomerFlowApi } from '../api/CustomerFlowApi';

// Gives the app's CustomerFlowApi; must be used inside CustomerFlowApiContext's provider.
export function useCustomerFlowApi(): CustomerFlowApi {
  const customerFlowApi = useContext(CustomerFlowApiContext);
  if (customerFlowApi === undefined) {
    throw new Error('useCustomerFlowApi must be used inside CustomerFlowApiContext.Provider');
  }
  return customerFlowApi;
}
