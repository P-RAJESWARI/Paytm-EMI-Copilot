import { describe, expect, it } from 'vitest';

import {
  LiveStatusStreamNetworkError,
  LiveStatusStreamUnavailableError,
} from '../api/openSaleStatusStream';
import { isExpectedStreamFailure } from './isExpectedStreamFailure';
import { LiveStatusStreamReadError } from './readServerSentEvents';

const OPEN_SIGNAL = new AbortController().signal;

describe('isExpectedStreamFailure', () => {
  it.each([
    ['the network failed', new LiveStatusStreamNetworkError()],
    ['no stream opened', new LiveStatusStreamUnavailableError()],
    ['the stream broke mid-read', new LiveStatusStreamReadError()],
    ['the request was aborted', new DOMException('Aborted', 'AbortError')],
  ])('treats "%s" as expected', (_description, error) => {
    expect(isExpectedStreamFailure(error, OPEN_SIGNAL)).toBe(true);
  });

  it.each([
    ['a plain error', new Error('Unexpected failure')],
    ['a TypeError from a bug, not from fetch', new TypeError('x is undefined')],
    ['a thrown non-error value', 'unexpected'],
  ])('treats "%s" as unexpected', (_description, error) => {
    expect(isExpectedStreamFailure(error, OPEN_SIGNAL)).toBe(false);
  });

  it('treats any error after the feed was stopped as expected', () => {
    const abortController = new AbortController();
    abortController.abort();

    expect(isExpectedStreamFailure(new Error('Unexpected failure'), abortController.signal)).toBe(
      true,
    );
  });
});
