const PAISE_PER_RUPEE = 100;
/** Up to ₹99,99,999 a month; the server validates the real limits. */
const MAXIMUM_BUDGET_DIGIT_COUNT = 7;

// Keeps what the customer typed as whole-rupee digits only: no symbols, no leading zeros, 7 digits.
export function readBudgetDigits(typedText: string): string {
  return typedText
    .replace(/[^0-9]/g, '')
    .replace(/^0+/, '')
    .slice(0, MAXIMUM_BUDGET_DIGIT_COUNT);
}

// Converts whole-rupee digits to integer paise for the API (money is never a float on the wire).
export function convertBudgetDigitsToPaise(budgetDigits: string): number {
  return Number(budgetDigits) * PAISE_PER_RUPEE;
}

// Gives the digits to show again for a budget already confirmed (always whole rupees here).
export function convertPaiseToBudgetDigits(budgetInPaise: number | undefined): string {
  return budgetInPaise === undefined ? '' : String(Math.floor(budgetInPaise / PAISE_PER_RUPEE));
}
