import { useContext } from 'react';

import { CustomerFlowContext, type CustomerFlowContextValue } from '../model/customerFlowContext';

// Gives the flow state, its dispatch and the session; must be used inside CustomerFlowProvider.
export function useCustomerFlow(): CustomerFlowContextValue {
  const contextValue = useContext(CustomerFlowContext);
  if (contextValue === undefined) {
    throw new Error('useCustomerFlow must be used inside CustomerFlowProvider');
  }
  return contextValue;
}
