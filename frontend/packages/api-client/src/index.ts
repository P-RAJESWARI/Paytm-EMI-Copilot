// Public API of the api-client: the generated schema types, the client factory, its middleware,
// the live sale-status event payload helpers and the problem-code reader.
import type { components } from './generated/backendApiSchema';

export type { components, operations, paths } from './generated/backendApiSchema';
export {
  createBackendApiClient,
  type BackendApiClient,
  type BackendApiClientOptions,
} from './createBackendApiClient';
export { createAuthorizationMiddleware } from './middleware/authorizationMiddleware';
export {
  CORRELATION_ID_HEADER,
  createCorrelationIdMiddleware,
} from './middleware/correlationIdMiddleware';
export { createRandomCorrelationId } from './middleware/createRandomCorrelationId';
export { readProblemCode, type ProblemDetails } from './problemDetails';
export {
  SALE_STATUS_EVENTS_PATH,
  SALE_STATUS_EVENT_NAME,
  SALE_STATUS_RESYNC_EVENT_NAME,
  isSaleStatus,
  parseSaleStatusEventPayload,
  type SaleStatus,
  type SaleStatusEventPayload,
} from './saleStatusEvents';

/** Every response and request schema by name, for example ApiSchemas['SaleSummaryResponse']. */
export type ApiSchemas = components['schemas'];
