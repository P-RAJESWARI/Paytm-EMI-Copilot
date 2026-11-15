// Public API of the customer-flow feature: the CustomerFlowApi port and its factory, the flow
// state machine, the session gate and the hooks every screen uses. The fixture has its own entry,
// fixture.ts, so that it stays out of the production bundle.
export { createCustomerFlowApi, readCustomerFlowApiMode } from './api/createCustomerFlowApi';
export type { CustomerFlowApiMode } from './api/createCustomerFlowApi';
export {
  CUSTOMER_QR_TOKEN_INVALID_CODE,
  CUSTOMER_SESSION_TOKEN_INVALID_CODE,
  CustomerApiError,
  isRequestOutcomeUnknown,
  isSessionLostError,
  readCustomerApiErrorCode,
} from './api/customerApiError';
export type * from './api/customerContractTypes';
export { CustomerFlowApiContext } from './api/customerFlowApiContext';
export type * from './api/CustomerFlowApi';
export { customerQueryKeys } from './api/customerQueryKeys';
export { CustomerSessionGate } from './containers/CustomerSessionGate';
export { useCustomerFlow } from './hooks/useCustomerFlow';
export { useCustomerFlowApi } from './hooks/useCustomerFlowApi';
export type * from './model/customerFlowState';
export { getProblemMessageKey } from './model/problemMessageKey';
export { SessionUnavailableScreen } from './components/SessionUnavailableScreen';
export { usePlanComparison } from './hooks/usePlanComparison';
export { useIdempotencyKeyPerIntent } from './hooks/useIdempotencyKeyPerIntent';
