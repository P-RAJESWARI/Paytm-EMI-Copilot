import { useEffect, useState } from 'react';

/** Browsers cap timers at about 24.8 days; anything later is simply checked again then. */
const LONGEST_TIMER_IN_MILLISECONDS = 2_147_483_647;

// Tells whether a UTC moment (such as a QR code's expiry) has passed, re-rendering when it does.
export function useHasMomentPassed(isoMoment: string | undefined): boolean {
  const [passedMoment, setPassedMoment] = useState<string | undefined>(undefined);
  useEffect(() => {
    if (isoMoment === undefined) return undefined;
    const millisecondsLeft = new Date(isoMoment).getTime() - Date.now();
    const expiryTimer = setTimeout(
      () => {
        setPassedMoment(isoMoment);
      },
      Math.min(Math.max(millisecondsLeft, 0), LONGEST_TIMER_IN_MILLISECONDS),
    );
    return () => {
      clearTimeout(expiryTimer);
    };
  }, [isoMoment]);
  return isoMoment !== undefined && passedMoment === isoMoment;
}
