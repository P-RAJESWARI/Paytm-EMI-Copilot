// Second public entry of the customer-flow feature: the design-sample FixtureCustomerFlowApi, for
// tests and VITE_CUSTOMER_FLOW_API=fixture. Kept out of index.ts so the production bundle never
// includes it; createCustomerFlowApi loads it with a dynamic import instead.
export { FixtureCustomerFlowApi } from './api/FixtureCustomerFlowApi';
export type { FixtureCustomerFlowApiOptions } from './api/FixtureCustomerFlowApi';
