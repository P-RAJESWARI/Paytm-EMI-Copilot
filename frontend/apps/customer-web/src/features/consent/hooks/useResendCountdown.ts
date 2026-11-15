import { useEffect, useState } from 'react';

const MILLISECONDS_PER_SECOND = 1000;

/** Seconds left before a new OTP can be asked for, and how to start counting. */
export interface ResendCountdown {
  secondsUntilResend: number;
  /** Starts counting down to a moment, in milliseconds since 1970. */
  countDownTo: (resendAvailableAtInMilliseconds: number) => void;
}

// Counts the seconds until a new OTP may be asked for (from resendAvailableAt or Retry-After),
// ticking once a second only while there is time left.
export function useResendCountdown(): ResendCountdown {
  const [resendAvailableAt, setResendAvailableAt] = useState<number | undefined>(undefined);
  const [now, setNow] = useState(0);
  useEffect(() => {
    if (resendAvailableAt === undefined) return undefined;
    const ticker = window.setInterval(() => {
      const tickTime = Date.now();
      setNow(tickTime);
      if (tickTime >= resendAvailableAt) window.clearInterval(ticker);
    }, MILLISECONDS_PER_SECOND);
    return () => {
      window.clearInterval(ticker);
    };
  }, [resendAvailableAt]);
  return {
    secondsUntilResend:
      resendAvailableAt === undefined
        ? 0
        : Math.max(0, Math.ceil((resendAvailableAt - now) / MILLISECONDS_PER_SECOND)),
    countDownTo: (resendAvailableAtInMilliseconds) => {
      setNow(Date.now());
      setResendAvailableAt(resendAvailableAtInMilliseconds);
    },
  };
}
