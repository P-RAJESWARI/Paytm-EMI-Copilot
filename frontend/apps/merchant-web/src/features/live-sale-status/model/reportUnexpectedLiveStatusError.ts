/** reportError as the browser may or may not provide it (older browsers and some test DOMs lack it). */
interface MaybeReportError {
  reportError?: (error: unknown) => void;
}

// Hands an unexpected live-feed error to the browser's error reporting (the window "error" event
// and the console) without throwing, so the feed keeps reconnecting; never adds tokens or headers.
export function reportUnexpectedLiveStatusError(error: unknown): void {
  const browserGlobal = globalThis as MaybeReportError;
  if (browserGlobal.reportError !== undefined) {
    // Called on the global object, as some browsers require for window functions.
    browserGlobal.reportError(error);
    return;
  }
  // eslint-disable-next-line no-console -- the fallback for browsers without reportError.
  console.error(error);
}
