import type { CustomerFlowApi } from './CustomerFlowApi';
import { FixtureCustomerFlowApi } from './FixtureCustomerFlowApi';
import { HttpCustomerFlowApi } from './HttpCustomerFlowApi';

/** `http` talks to the backend (the default everywhere); `fixture` answers the design sample. */
export type CustomerFlowApiMode = 'http' | 'fixture';

export interface CreateCustomerFlowApiOptions {
  mode: CustomerFlowApiMode;
  baseUrl: string;
  fetchFunction: (request: Request) => Promise<Response>;
}

// Reads the mode from VITE_CUSTOMER_FLOW_API: only the exact value "fixture" picks the fixture,
// so a production build can never fall back to sample data by accident.
export function readCustomerFlowApiMode(configuredMode: string | undefined): CustomerFlowApiMode {
  return configuredMode === 'fixture' ? 'fixture' : 'http';
}

// Pattern: Factory. Picks the CustomerFlowApi implementation in one place; screens never know which.
export function createCustomerFlowApi({
  mode,
  baseUrl,
  fetchFunction,
}: CreateCustomerFlowApiOptions): CustomerFlowApi {
  return mode === 'fixture'
    ? new FixtureCustomerFlowApi()
    : new HttpCustomerFlowApi({ baseUrl, fetchFunction });
}
