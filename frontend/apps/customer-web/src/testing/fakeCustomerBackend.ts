import type { CustomerProblemDetailsResponse } from '../features/customer-flow';

/** One handled request: the route's path parameters and the request itself. */
export interface FakeRouteContext {
  request: Request;
  pathParameters: Record<string, string>;
  searchParameters: URLSearchParams;
}

export type FakeRouteHandler = (context: FakeRouteContext) => Response | Promise<Response>;

/** Routes keyed "METHOD /api/v1/path/{parameter}", for example "GET /api/v1/customer-sessions/{customerSessionId}/plans". */
export type FakeRoutes = Record<string, FakeRouteHandler>;

export interface RecordedRequest {
  method: string;
  path: string;
  headers: Headers;
  body: unknown;
}

export interface FakeCustomerBackend {
  fetchFunction: (request: Request) => Promise<Response>;
  /** Every request the app sent, in order. */
  recordedRequests: RecordedRequest[];
  /** Adds or replaces routes while a test runs. */
  setRoutes: (routes: FakeRoutes) => void;
}

// Answers with a JSON body, as the API does on success.
export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

// Answers with an RFC 7807 problem carrying the given stable code and any extension members.
export function problemResponse(
  status: number,
  code: string,
  headers: Record<string, string> = {},
  extensionMembers: Partial<CustomerProblemDetailsResponse> = {},
): Response {
  const problem: CustomerProblemDetailsResponse = {
    ...extensionMembers,
    type: `https://emicopilot.example/problems/${code.toLowerCase()}`,
    title: code,
    status,
    detail: 'English developer detail that the UI must never show.',
    code,
    correlationId: 'test-correlation-id',
  };
  return new Response(JSON.stringify(problem), {
    status,
    headers: { 'Content-Type': 'application/problem+json', ...headers },
  });
}

// Answers with a server error and no problem body, as a proxy or a crashed server might.
export function bodylessErrorResponse(status: number): Response {
  return new Response('<html>Bad gateway</html>', {
    status,
    headers: { 'Content-Type': 'text/html' },
  });
}

// Fails the request the way fetch does when the shop's internet drops.
export function networkFailure(): Promise<Response> {
  return Promise.reject(new TypeError('Failed to fetch'));
}

// Turns "/api/v1/customer-sessions/{customerSessionId}/plans" into a matcher.
function matchPath(pattern: string, path: string): Record<string, string> | undefined {
  const patternParts = pattern.split('/');
  const pathParts = path.split('/');
  if (patternParts.length !== pathParts.length) return undefined;
  const pathParameters: Record<string, string> = {};
  for (const [index, patternPart] of patternParts.entries()) {
    const pathPart = pathParts[index] ?? '';
    if (patternPart.startsWith('{') && patternPart.endsWith('}')) {
      pathParameters[patternPart.slice(1, -1)] = decodeURIComponent(pathPart);
    } else if (patternPart !== pathPart) {
      return undefined;
    }
  }
  return pathParameters;
}

// Reads a request body as JSON for the record; an empty or non-JSON body is kept as text.
async function readRecordedBody(request: Request): Promise<unknown> {
  const text = await request.clone().text();
  if (text === '') return undefined;
  try {
    return JSON.parse(text);
  } catch (error) {
    if (error instanceof SyntaxError) return text;
    throw error;
  }
}

// Pattern: Fake. A stand-in for the backend: routes requests to handlers and records them,
// so API tests run with no network. An unknown route answers 404 RESOURCE_NOT_FOUND.
export function createFakeCustomerBackend(initialRoutes: FakeRoutes = {}): FakeCustomerBackend {
  let routes: FakeRoutes = { ...initialRoutes };
  const recordedRequests: RecordedRequest[] = [];
  // Records the request, then answers with the first route whose method and path match.
  async function fetchFunction(request: Request): Promise<Response> {
    const url = new URL(request.url);
    recordedRequests.push({
      method: request.method,
      path: url.pathname + url.search,
      headers: request.headers,
      body: await readRecordedBody(request),
    });
    for (const [routeKey, handler] of Object.entries(routes)) {
      const [method, pattern] = routeKey.split(' ');
      if (method !== request.method || pattern === undefined) continue;
      const pathParameters = matchPath(pattern, url.pathname);
      if (pathParameters !== undefined) {
        return handler({ request, pathParameters, searchParameters: url.searchParams });
      }
    }
    return problemResponse(404, 'RESOURCE_NOT_FOUND');
  }
  return {
    fetchFunction,
    recordedRequests,
    setRoutes: (nextRoutes) => {
      routes = { ...routes, ...nextRoutes };
    },
  };
}
