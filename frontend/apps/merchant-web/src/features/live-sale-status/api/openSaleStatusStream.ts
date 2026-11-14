import { SALE_STATUS_EVENTS_PATH } from '@emi-copilot/api-client';

/** The stream answered, but not with an open event stream. */
export class LiveStatusStreamUnavailableError extends Error {}

/** The stream could not be reached: fetch failed at the network level (a TypeError). */
export class LiveStatusStreamNetworkError extends Error {}

/** Where and as whom to open the shop's live sale-status stream. */
export interface SaleStatusStreamConnection {
  fetchFunction: (request: Request) => Promise<Response>;
  baseUrl: string;
  accessToken: string;
}

// Calls fetch, turning its network failure (a TypeError, by the Fetch standard) into a
// LiveStatusStreamNetworkError so callers can tell it from a bug; anything else is rethrown as is.
async function fetchSaleStatusStream(
  connection: SaleStatusStreamConnection,
  request: Request,
): Promise<Response> {
  try {
    return await connection.fetchFunction(request);
  } catch (error) {
    if (error instanceof TypeError) {
      throw new LiveStatusStreamNetworkError('The live status stream could not be reached.', {
        cause: error,
      });
    }
    throw error;
  }
}

// Opens GET /sales/events with the token in the Authorization header (never in a URL); gives the
// event-stream body, undefined on 401, and throws when no stream opened.
export async function openSaleStatusStream(
  connection: SaleStatusStreamConnection,
  signal: AbortSignal,
): Promise<ReadableStream<Uint8Array> | undefined> {
  const response = await fetchSaleStatusStream(
    connection,
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
