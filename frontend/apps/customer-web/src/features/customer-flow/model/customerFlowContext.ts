import { createContext, type Dispatch } from 'react';

import type { CustomerSession } from '../api/CustomerFlowApi';
import type { CustomerFlowAction, CustomerFlowState } from './customerFlowState';

/** The flow position and answers, the way to change them, and the session the flow belongs to. */
export interface CustomerFlowContextValue {
  state: CustomerFlowState;
  dispatch: Dispatch<CustomerFlowAction>;
  session: CustomerSession;
}

export const CustomerFlowContext = createContext<CustomerFlowContextValue | undefined>(undefined);
