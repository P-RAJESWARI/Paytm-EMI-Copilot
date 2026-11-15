const SECONDS_PER_MINUTE = 60;

// Gives "0:24" for 24 seconds and "1:05" for 65, as the C9 resend line shows it.
export function formatCountdown(remainingSeconds: number): string {
  const wholeSeconds = Math.max(0, Math.ceil(remainingSeconds));
  const minutes = Math.floor(wholeSeconds / SECONDS_PER_MINUTE);
  const seconds = wholeSeconds % SECONDS_PER_MINUTE;
  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}
