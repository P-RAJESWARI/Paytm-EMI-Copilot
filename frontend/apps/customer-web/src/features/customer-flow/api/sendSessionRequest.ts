import {
  CORRELATION_ID_HEADER,
  CUSTOMER_SESSION_TOKEN_HEADER,
  createRandomCorrelationId,
} from '@emi-copilot/api-client';

import { readApiData } from './readApiData';

/** One call to a session endpoint that the generated client cannot type yet (raw audio, binary). */
export interface SessionRequest {
  baseUrl: string;
  fetchFunction: (request: Request) => Promise<Response>;
  sessionToken: string;
  /** Path under the base URL, for example /api/v1/customer-sessions/{id}/speech/synthesis. */
  path: string;
  /** Raw audio bytes or a JSON string. */
  body: ArrayBuffer | string;
  contentType: string;
  /** Accept-Language for calls whose answer has human-readable text. */
  language?: string | undefined;
}

// Reads a failed answer's problem+json body; anything unreadable counts as no body.
async function readErrorBody(response: Response): Promise<unknown> {
  try {
    return (await response.json()) as unknown;
  } catch {
    return undefined;
  }
}

// Sends one POST with the session token and a correlation id, and gives the successful Response;
// a failure becomes the same CustomerApiError the generated-client calls raise (via readApiData).
// Used for the Layer 4 raw-audio and binary-audio calls (frontend.md section 9 fallback wrapper).
export async function sendSessionRequest(request: SessionRequest): Promise<Response> {
  const headers = new Headers({
    'Content-Type': request.contentType,
    [CUSTOMER_SESSION_TOKEN_HEADER]: request.sessionToken,
    [CORRELATION_ID_HEADER]: createRandomCorrelationId(),
  });
  if (request.language !== undefined) headers.set('Accept-Language', request.language);
  const pendingResponse = request.fetchFunction(
    new Request(`${request.baseUrl}${request.path}`, {
      method: 'POST',
      headers,
      body: request.body,
    }),
  );
  return readApiData(
    pendingResponse.then(async (response) =>
      response.ok
        ? { data: response, response }
        : { error: await readErrorBody(response), response },
    ),
  );
}
