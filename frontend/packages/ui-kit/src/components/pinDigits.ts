// Keeps only the ASCII digits 0-9 from typed or pasted text.
export function extractDigits(text: string): string {
  return text.replace(/[^0-9]/g, '');
}

// Gives the PIN after one box changed: the box's new digits replace it, later digits stay in place.
export function replaceDigitsAtPosition(
  currentDigits: string,
  position: number,
  newDigits: string,
  digitCount: number,
): string {
  const tailStart = position + Math.max(1, newDigits.length);
  return (currentDigits.slice(0, position) + newDigits + currentDigits.slice(tailStart)).slice(
    0,
    digitCount,
  );
}

// Removes the digit a box held from what the browser reports, leaving only what was just typed.
export function digitsTypedIntoBox(boxValue: string, digitTheBoxHeld: string | undefined): string {
  const allDigits = extractDigits(boxValue);
  return digitTheBoxHeld === undefined ? allDigits : allDigits.replace(digitTheBoxHeld, '');
}
