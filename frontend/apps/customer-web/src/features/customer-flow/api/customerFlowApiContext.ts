import { createContext } from 'react';

import type { CustomerFlowApi } from './CustomerFlowApi';

/** The app's one CustomerFlowApi (fixture or HTTP), chosen by the factory at start-up. */
export const CustomerFlowApiContext = createContext<CustomerFlowApi | undefined>(undefined);
