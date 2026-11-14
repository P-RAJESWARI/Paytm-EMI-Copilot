import type { components, paths } from './generated/backendApiSchema';

export type SaleStatus = components['schemas']['SaleStatus'];

/** The data of one `sale-status` event on GET /api/v1/sales/events. */
export type SaleStatusEventPayload = components['schemas']['SaleStatusEventPayload'];

export const SALE_STATUS_EVENTS_PATH = '/api/v1/sales/events' satisfies keyof paths;

/** Event names on the stream: a status change, or "read the counter list again". */
export const SALE_STATUS_EVENT_NAME = 'sale-status';
export const SALE_STATUS_RESYNC_EVENT_NAME = 'resync';

// A Record, so the compiler fails here if the API adds a status this list does not know.
const IS_KNOWN_SALE_STATUS: Record<SaleStatus, true> = {
  CHOOSING: true,
  READY_TO_PAY: true,
  PAID: true,
  PAYMENT_NOT_COMPLETED: true,
  EXPIRED: true,
};

// Narrows any value to one of the API's sale statuses.
export function isSaleStatus(value: unknown): value is SaleStatus {
  return typeof value === 'string' && Object.hasOwn(IS_KNOWN_SALE_STATUS, value);
}

// Reads the data line of a `sale-status` event; gives undefined for anything that is not exactly
// a valid payload, so a malformed event is skipped instead of breaking the live list.
export function parseSaleStatusEventPayload(eventData: string): SaleStatusEventPayload | undefined {
  let parsedData: unknown;
  try {
    parsedData = JSON.parse(eventData);
  } catch (error) {
    if (error instanceof SyntaxError) return undefined;
    throw error;
  }
  if (typeof parsedData !== 'object' || parsedData === null) return undefined;
  const { saleId, status, statusChangedAt } = parsedData as Record<string, unknown>;
  if (typeof saleId !== 'string' || typeof statusChangedAt !== 'string' || !isSaleStatus(status)) {
    return undefined;
  }
  return { saleId, status, statusChangedAt };
}
