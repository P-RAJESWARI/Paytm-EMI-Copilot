const RUPEE_SYMBOL = '₹';
const PAISE_PER_RUPEE = 100;
const HALF_RUPEE_IN_PAISE = 50;
const INDIAN_LAST_GROUP_SIZE = 3;
const INDIAN_LEADING_GROUP_SIZE = 2;

// Rejects anything that is not a whole, non-negative, exactly representable number of paise.
function assertValidPaise(amountInPaise: number): void {
  if (!Number.isSafeInteger(amountInPaise) || amountInPaise < 0) {
    throw new RangeError('An amount in paise must be a non-negative safe integer.');
  }
}

// Groups digits as in India: the last three, then pairs (184000 gives "1,84,000").
export function groupDigitsTheIndianWay(wholeNumber: number): string {
  assertValidPaise(wholeNumber);
  const digits = String(wholeNumber);
  const lastGroup = digits.slice(-INDIAN_LAST_GROUP_SIZE);
  let leadingDigits = digits.slice(0, -INDIAN_LAST_GROUP_SIZE);
  const leadingGroups: string[] = [];
  while (leadingDigits !== '') {
    leadingGroups.unshift(leadingDigits.slice(-INDIAN_LEADING_GROUP_SIZE));
    leadingDigits = leadingDigits.slice(0, -INDIAN_LEADING_GROUP_SIZE);
  }
  return [...leadingGroups, lastGroup].join(',');
}

// Gives "₹3,667" for 366667 paise: whole rupees, paise rounded half-up, Indian grouping.
// Mirrors the backend's format_paise_as_whole_rupees so screen text matches sent text.
export function formatRupeesFromPaise(amountInPaise: number): string {
  assertValidPaise(amountInPaise);
  const leftoverPaise = amountInPaise % PAISE_PER_RUPEE;
  // Integer arithmetic only: subtracting the leftover first makes the division exact.
  const wholeRupees =
    (amountInPaise - leftoverPaise) / PAISE_PER_RUPEE +
    (leftoverPaise >= HALF_RUPEE_IN_PAISE ? 1 : 0);
  return RUPEE_SYMBOL + groupDigitsTheIndianWay(wholeRupees);
}

// Gives "₹3,666.67" for 366667 paise, for the rare place that must show paise exactly.
export function formatRupeesWithPaiseFromPaise(amountInPaise: number): string {
  assertValidPaise(amountInPaise);
  const leftoverPaise = amountInPaise % PAISE_PER_RUPEE;
  const wholeRupees = (amountInPaise - leftoverPaise) / PAISE_PER_RUPEE;
  return `${RUPEE_SYMBOL}${groupDigitsTheIndianWay(wholeRupees)}.${String(leftoverPaise).padStart(2, '0')}`;
}
