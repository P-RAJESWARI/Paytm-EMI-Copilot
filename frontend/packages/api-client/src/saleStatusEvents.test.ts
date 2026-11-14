import { describe, expect, it, vi } from 'vitest';

import { isSaleStatus, parseSaleStatusEventPayload } from './saleStatusEvents';

describe('parseSaleStatusEventPayload', () => {
  it('reads a valid sale-status payload', () => {
    const eventData =
      '{"saleId":"01JD5Z0Q8M6X3V2N7B4C9K1T0F","status":"READY_TO_PAY","statusChangedAt":"2026-11-15T09:36:00Z"}';

    expect(parseSaleStatusEventPayload(eventData)).toEqual({
      saleId: '01JD5Z0Q8M6X3V2N7B4C9K1T0F',
      status: 'READY_TO_PAY',
      statusChangedAt: '2026-11-15T09:36:00Z',
    });
  });

  it('keeps only the three documented fields', () => {
    const eventData =
      '{"saleId":"sale-1","status":"PAID","statusChangedAt":"2026-11-15T09:36:00Z","extra":"ignored"}';

    expect(parseSaleStatusEventPayload(eventData)).toEqual({
      saleId: 'sale-1',
      status: 'PAID',
      statusChangedAt: '2026-11-15T09:36:00Z',
    });
  });

  it.each([
    ['malformed JSON', '{"saleId":'],
    ['a JSON array', '[]'],
    ['JSON null', 'null'],
    ['the empty resync object', '{}'],
    ['an unknown status', '{"saleId":"s","status":"APPROVED","statusChangedAt":"t"}'],
    ['a numeric sale id', '{"saleId":7,"status":"PAID","statusChangedAt":"t"}'],
    ['a missing timestamp', '{"saleId":"s","status":"PAID"}'],
  ])('skips %s', (_description, eventData) => {
    expect(parseSaleStatusEventPayload(eventData)).toBeUndefined();
  });

  it('does not hide errors other than malformed JSON', () => {
    vi.spyOn(JSON, 'parse').mockImplementation(() => {
      throw new TypeError('unexpected');
    });

    expect(() => parseSaleStatusEventPayload('{}')).toThrow(TypeError);
  });
});

describe('isSaleStatus', () => {
  it('accepts the five merchant-visible statuses only', () => {
    expect(
      ['CHOOSING', 'READY_TO_PAY', 'PAID', 'PAYMENT_NOT_COMPLETED', 'EXPIRED'].every(isSaleStatus),
    ).toBe(true);
    expect(isSaleStatus('toString')).toBe(false);
    expect(isSaleStatus(3)).toBe(false);
  });
});
