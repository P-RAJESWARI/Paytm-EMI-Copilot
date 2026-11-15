import { useCallback, useMemo, useReducer, type ReactNode } from 'react';

import type { CustomerSession } from '../api/CustomerFlowApi';
import { useSessionLossWatcher } from '../hooks/useSessionLossWatcher';
import { CustomerFlowContext } from '../model/customerFlowContext';
import { customerFlowReducer } from '../model/customerFlowReducer';
import { INITIAL_CUSTOMER_FLOW_STATE, type CustomerFlowState } from '../model/customerFlowState';

export interface CustomerFlowProviderProps {
  session: CustomerSession;
  children: ReactNode;
  /** Starts at another step; only tests pass it. */
  initialState?: CustomerFlowState | undefined;
}

// Holds the customer flow's one reducer for an open session and ends the flow when the server
// says the session is gone.
export function CustomerFlowProvider({
  session,
  children,
  initialState = INITIAL_CUSTOMER_FLOW_STATE,
}: CustomerFlowProviderProps) {
  const [state, dispatch] = useReducer(customerFlowReducer, initialState);
  const handleSessionLost = useCallback(() => {
    dispatch({ type: 'sessionLost' });
  }, []);
  useSessionLossWatcher(handleSessionLost);
  const contextValue = useMemo(() => ({ state, dispatch, session }), [state, session]);
  return (
    <CustomerFlowContext.Provider value={contextValue}>{children}</CustomerFlowContext.Provider>
  );
}
