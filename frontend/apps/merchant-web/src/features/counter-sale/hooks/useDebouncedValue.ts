import { useEffect, useState } from 'react';

// Gives the value only after it has stopped changing for the delay, so typing in the search
// box sends one request instead of one per letter.
export function useDebouncedValue<Value>(value: Value, delayInMilliseconds: number): Value {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      setDebouncedValue(value);
    }, delayInMilliseconds);
    return () => {
      clearTimeout(debounceTimer);
    };
  }, [value, delayInMilliseconds]);
  return debouncedValue;
}
