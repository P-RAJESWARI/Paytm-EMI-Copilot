import { afterEach, describe, expect, it, vi } from 'vitest';

import { reportUnexpectedLiveStatusError } from './reportUnexpectedLiveStatusError';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('reportUnexpectedLiveStatusError', () => {
  it('hands the error to the browser reportError when it exists', () => {
    const reportError = vi.fn();
    vi.stubGlobal('reportError', reportError);
    const error = new Error('Unexpected failure');

    reportUnexpectedLiveStatusError(error);

    expect(reportError).toHaveBeenCalledExactlyOnceWith(error);
  });

  it('falls back to the console where reportError is missing', () => {
    vi.stubGlobal('reportError', undefined);
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const error = new Error('Unexpected failure');

    reportUnexpectedLiveStatusError(error);

    expect(consoleError).toHaveBeenCalledExactlyOnceWith(error);
  });
});
