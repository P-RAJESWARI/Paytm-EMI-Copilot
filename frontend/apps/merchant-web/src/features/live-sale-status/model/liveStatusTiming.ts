/** After this many failed connections in a row, the counter list is also polled. */
export const POLLING_FALLBACK_FAILURE_COUNT = 3;

/** How often the fallback polling refreshes the open sale screens. */
export const POLLING_INTERVAL_IN_MILLISECONDS = 5_000;

const FIRST_RECONNECT_DELAY_IN_MILLISECONDS = 1_000;
const LONGEST_RECONNECT_DELAY_IN_MILLISECONDS = 30_000;

// Gives the wait before the next connection attempt: 1 s, 2 s, 4 s and so on, never above 30 s.
export function getReconnectDelayInMilliseconds(consecutiveFailureCount: number): number {
  const exponent = Math.max(0, consecutiveFailureCount - 1);
  return Math.min(
    FIRST_RECONNECT_DELAY_IN_MILLISECONDS * 2 ** exponent,
    LONGEST_RECONNECT_DELAY_IN_MILLISECONDS,
  );
}
