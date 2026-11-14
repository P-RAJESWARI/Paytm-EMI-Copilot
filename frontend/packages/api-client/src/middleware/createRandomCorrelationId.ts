const UUID_BYTE_COUNT = 16;
const VERSION_BYTE_INDEX = 6;
const VARIANT_BYTE_INDEX = 8;

// Makes a random UUID v4 with getRandomValues, which (unlike crypto.randomUUID) also works when
// a counter tablet opens the app over plain http on the shop's network.
export function createRandomCorrelationId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(UUID_BYTE_COUNT));
  bytes[VERSION_BYTE_INDEX] = ((bytes[VERSION_BYTE_INDEX] ?? 0) & 0x0f) | 0x40;
  bytes[VARIANT_BYTE_INDEX] = ((bytes[VARIANT_BYTE_INDEX] ?? 0) & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
