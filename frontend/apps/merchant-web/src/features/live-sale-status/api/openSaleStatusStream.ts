import { SALE_STATUS_EVENTS_PATH } from '@emi-copilot/api-client';

/** The stream answered, but not with an open event stream. */
export class LiveStatusStreamUnavailableError extends Error {}

/** Where and as whom to open the shop's live sale-status stream. */
export interface SaleStatusStreamConnection {
  fetchFunction: (request: Request) => Promise<Response>;
  baseUrl: string;
  accessToken: string;
}

// Opens GET /sales/events with the token in the Authorization header (never in a URL); gives the
// event-stream body, undefined on 401, and throws when no stream opened.
export async function openSaleStatusStream(
  connection: SaleStatusStreamConnection,
  signal: AbortSignal,
): Promise<ReadableStream<Uint8Array> | undefined> {
  const response = await connection.fetchFunction(
    new Request(`${connection.baseUrl}${SALE_STATUS_EVENTS_PATH}`, {
      headers: { Authorization: `Bearer ${connection.accessToken}`, Accept: 'text/event-stream' },
      cache: 'no-store',
      signal,
    }),
  );
  if (response.status === 401) return undefined;
  if (!response.ok || response.body === null) throw new LiveStatusStreamUnavailableError();
  return response.body;
}
