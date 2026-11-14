/** The two M1 fields as typed. */
export interface PairingFormValues {
  shopId: string;
  pin: string;
}

/** Same rule as PairDeviceRequest.shopId in backend/openapi.json. */
export const SHOP_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9-]{0,31}$/;

export const PAIRING_PIN_DIGIT_COUNT = 6;

const PIN_PATTERN = new RegExp(`^[0-9]{${PAIRING_PIN_DIGIT_COUNT}}$`);

// Checks the PIN has exactly six digits; gives the translation key of the problem, or true.
export function validatePairingPin(pin: string): true | string {
  return PIN_PATTERN.test(pin) ? true : 'pairing.validation.pinIncomplete';
}

// Checks the shop ID is filled in and shaped like one; gives the translation key of the problem, or true.
export function validateShopId(shopId: string): true | string {
  const trimmedShopId = shopId.trim();
  if (trimmedShopId === '') return 'pairing.validation.shopIdRequired';
  return SHOP_ID_PATTERN.test(trimmedShopId) ? true : 'pairing.validation.shopIdFormat';
}
