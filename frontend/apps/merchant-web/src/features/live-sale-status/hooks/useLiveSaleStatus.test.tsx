import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
  type Mock,
  type MockInstance,
} from 'vitest';

import { MerchantApiProvider } from '../../../shared/api/MerchantApiProvider';
import { COUNTER_SALES_QUERY_KEY } from '../../../shared/api/saleQueryKeys';
import { MerchantSessionProvider } from '../../../shared/session/MerchantSessionProvider';
import { useMerchantSession } from '../../../shared/session/useMerchantSession';
import { createControllableEventStream } from '../../../testing/controllableEventStream';
import { problemResponse } from '../../../testing/fakeMerchantBackend';
import { TEST_MERCHANT_SESSION } from '../../../testing/merchantTestData';
import { createTestQueryClient } from '../../../testing/renderMerchantApp';
import { useLiveSaleStatus } from './useLiveSaleStatus';

type FetchFunction = (request: Request) => Promise<Response>;

// Renders the hook (and the session, to see sign-outs) with a fake fetch and a spied cache.
function renderLiveSaleStatus(fetchFunction: FetchFunction) {
  const queryClient = createTestQueryClient();
  const invalidateQueries = vi.spyOn(queryClient, 'invalidateQueries');
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MerchantSessionProvider initialSession={TEST_MERCHANT_SESSION}>
          <MerchantApiProvider fetchFunction={fetchFunction}>{children}</MerchantApiProvider>
        </MerchantSessionProvider>
      </QueryClientProvider>
    );
  }
  const hookResult = renderHook(
    () => ({ liveStatus: useLiveSaleStatus(), session: useMerchantSession().session }),
    { wrapper: Wrapper },
  );
  return { ...hookResult, invalidateQueries };
}

// Lets pending promises and the given fake time run.
async function advance(milliseconds: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(milliseconds);
  });
}

// The query keys the cache was asked to refresh, in order.
function invalidatedKeys(
  invalidateQueries: MockInstance<QueryClient['invalidateQueries']>,
): unknown[] {
  return invalidateQueries.mock.calls.map((call) => call[0]?.queryKey);
}

let reportError: Mock<(error: unknown) => void>;

beforeEach(() => {
  vi.useFakeTimers();
  reportError = vi.fn();
  vi.stubGlobal('reportError', reportError);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('useLiveSaleStatus', () => {
  it('opens the stream with the token in the Authorization header, never in the URL', async () => {
    const eventStream = createControllableEventStream();
    const fetchFunction = vi.fn<FetchFunction>(() => Promise.resolve(eventStream.createResponse()));

    renderLiveSaleStatus(fetchFunction);
    await advance(0);

    const request = fetchFunction.mock.calls[0]?.[0];
    expect(new URL(request?.url ?? '').pathname).toBe('/api/v1/sales/events');
    expect(request?.url).not.toContain(TEST_MERCHANT_SESSION.accessToken);
    expect(request?.headers.get('Authorization')).toBe(
      `Bearer ${TEST_MERCHANT_SESSION.accessToken}`,
    );
    expect(request?.headers.get('Accept')).toBe('text/event-stream');
  });

  it('refreshes the counter list and that sale on a status event, and everything on resync', async () => {
    const eventStream = createControllableEventStream();
    const { invalidateQueries } = renderLiveSaleStatus(() =>
      Promise.resolve(eventStream.createResponse()),
    );
    await advance(0);

    eventStream.send(
      ': heartbeat\n\nevent: sale-status\ndata: {"saleId":"sale-1","status":"READY_TO_PAY",',
    );
    eventStream.send('"statusChangedAt":"2026-11-15T09:36:00Z"}\n\n');
    await advance(0);
    expect(invalidatedKeys(invalidateQueries)).toEqual([
      COUNTER_SALES_QUERY_KEY,
      ['sale', 'sale-1'],
    ]);

    eventStream.send('event: resync\ndata: {}\n\n');
    await advance(0);
    expect(invalidatedKeys(invalidateQueries).at(-1)).toEqual(['sale']);
  });

  it('skips malformed and unknown events', async () => {
    const eventStream = createControllableEventStream();
    const { invalidateQueries } = renderLiveSaleStatus(() =>
      Promise.resolve(eventStream.createResponse()),
    );
    await advance(0);

    eventStream.send('event: sale-status\ndata: {"saleId":1}\n\nevent: other\ndata: {}\n\n');
    await advance(0);

    expect(invalidateQueries).not.toHaveBeenCalled();
  });

  it('reconnects with growing waits and catches up once connected again', async () => {
    const firstStream = createControllableEventStream();
    const secondStream = createControllableEventStream();
    const fetchFunction = vi
      .fn<FetchFunction>()
      .mockResolvedValueOnce(firstStream.createResponse())
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(secondStream.createResponse());
    const { invalidateQueries } = renderLiveSaleStatus(fetchFunction);
    await advance(0);
    expect(fetchFunction).toHaveBeenCalledTimes(1);

    firstStream.close();
    await advance(999);
    expect(fetchFunction).toHaveBeenCalledTimes(1);
    await advance(1);
    expect(fetchFunction).toHaveBeenCalledTimes(2);
    await advance(2_000);
    expect(fetchFunction).toHaveBeenCalledTimes(3);
    expect(invalidatedKeys(invalidateQueries)).toEqual([['sale']]);
    expect(reportError).not.toHaveBeenCalled();
  });

  it('polls every five seconds after three failures in a row, and stops once live again', async () => {
    const eventStream = createControllableEventStream();
    const fetchFunction = vi
      .fn<FetchFunction>()
      .mockResolvedValueOnce(problemResponse(503, 'SERVICE_UNAVAILABLE'))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(eventStream.createResponse());
    const { result, invalidateQueries } = renderLiveSaleStatus(fetchFunction);
    await advance(0);
    await advance(1_000);
    await advance(2_000);
    expect(result.current.liveStatus.isPolling).toBe(true);

    await advance(4_000);
    expect(fetchFunction).toHaveBeenCalledTimes(4);
    expect(result.current.liveStatus.isPolling).toBe(false);
    const callsWhenLive = invalidateQueries.mock.calls.length;
    await advance(10_000);
    expect(invalidateQueries.mock.calls.length).toBe(callsWhenLive);
    expect(invalidatedKeys(invalidateQueries)).toContainEqual(['sale']);
  });

  it('keeps polling every five seconds while the stream stays down', async () => {
    const fetchFunction = vi.fn<FetchFunction>(() =>
      Promise.reject(new TypeError('Failed to fetch')),
    );
    const { result, invalidateQueries } = renderLiveSaleStatus(fetchFunction);
    await advance(0);
    await advance(1_000 + 2_000);
    expect(result.current.liveStatus.isPolling).toBe(true);

    await advance(5_000);
    await advance(5_000);

    expect(invalidatedKeys(invalidateQueries)).toEqual([['sale'], ['sale']]);
    expect(reportError).not.toHaveBeenCalled();
  });

  it('reconnects without reporting when the stream breaks mid-read', async () => {
    const brokenStream = createControllableEventStream();
    const nextStream = createControllableEventStream();
    const fetchFunction = vi
      .fn<FetchFunction>()
      .mockResolvedValueOnce(brokenStream.createResponse())
      .mockResolvedValueOnce(nextStream.createResponse());
    renderLiveSaleStatus(fetchFunction);
    await advance(0);

    brokenStream.fail(new TypeError('network error'));
    await advance(1_000);

    expect(fetchFunction).toHaveBeenCalledTimes(2);
    expect(reportError).not.toHaveBeenCalled();
  });

  it('reports an unexpected error, yet still reconnects and falls back to polling', async () => {
    const unexpectedError = new Error('Unexpected failure');
    const fetchFunction = vi.fn<FetchFunction>(() => Promise.reject(unexpectedError));
    const { result, invalidateQueries } = renderLiveSaleStatus(fetchFunction);
    await advance(0);

    expect(reportError).toHaveBeenCalledExactlyOnceWith(unexpectedError);
    await advance(1_000 + 2_000);
    expect(fetchFunction).toHaveBeenCalledTimes(3);
    expect(result.current.liveStatus.isPolling).toBe(true);
    await advance(5_000);

    expect(reportError).toHaveBeenCalledTimes(fetchFunction.mock.calls.length);
    expect(invalidatedKeys(invalidateQueries)).toContainEqual(['sale']);
  });

  it('reports an error thrown while applying an event, and reconnects', async () => {
    const firstStream = createControllableEventStream();
    const secondStream = createControllableEventStream();
    const fetchFunction = vi
      .fn<FetchFunction>()
      .mockResolvedValueOnce(firstStream.createResponse())
      .mockResolvedValueOnce(secondStream.createResponse());
    const { invalidateQueries } = renderLiveSaleStatus(fetchFunction);
    await advance(0);
    const handlingError = new TypeError('Cannot read the cache');
    invalidateQueries.mockImplementationOnce(() => {
      throw handlingError;
    });

    firstStream.send('event: resync\ndata: {}\n\n');
    await advance(1_000);

    expect(reportError).toHaveBeenCalledExactlyOnceWith(handlingError);
    expect(fetchFunction).toHaveBeenCalledTimes(2);
  });

  it('signs out when the stream says the token is no longer valid', async () => {
    const fetchFunction = vi.fn<FetchFunction>(() =>
      Promise.resolve(problemResponse(401, 'MERCHANT_AUTHENTICATION_REQUIRED')),
    );
    const { result } = renderLiveSaleStatus(fetchFunction);

    await advance(0);

    expect(result.current.session).toBeUndefined();
    await advance(60_000);
    expect(fetchFunction).toHaveBeenCalledTimes(1);
  });

  it('closes the stream and stops reconnecting on unmount', async () => {
    const eventStream = createControllableEventStream();
    const fetchFunction = vi.fn<FetchFunction>(() => Promise.resolve(eventStream.createResponse()));
    const { unmount } = renderLiveSaleStatus(fetchFunction);
    await advance(0);

    unmount();
    await advance(60_000);

    expect(fetchFunction.mock.calls[0]?.[0].signal.aborted).toBe(true);
    expect(fetchFunction).toHaveBeenCalledTimes(1);
  });
});
