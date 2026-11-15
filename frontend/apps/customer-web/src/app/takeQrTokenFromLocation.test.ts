import { describe, expect, it, vi } from 'vitest';

import { takeQrTokenFromLocation } from './takeQrTokenFromLocation';

// Builds a location and a history spy for one URL.
function browserAt(hash: string) {
  const replaceState = vi.fn();
  return {
    access: {
      location: { hash, pathname: '/', search: '?from=qr' },
      history: { state: { previous: true }, replaceState },
    },
    replaceState,
  };
}

describe('takeQrTokenFromLocation', () => {
  it('reads the token from #t= and removes the fragment from the address bar', () => {
    const browser = browserAt('#t=qr-token-4821');

    expect(takeQrTokenFromLocation(browser.access)).toBe('qr-token-4821');
    expect(browser.replaceState).toHaveBeenCalledWith({ previous: true }, '', '/?from=qr');
  });

  it('gives undefined without a fragment and leaves history alone', () => {
    const browser = browserAt('');

    expect(takeQrTokenFromLocation(browser.access)).toBeUndefined();
    expect(browser.replaceState).not.toHaveBeenCalled();
  });

  it('removes any other fragment too, and gives undefined for an empty token', () => {
    const otherFragment = browserAt('#section');
    const emptyToken = browserAt('#t=%20');

    expect(takeQrTokenFromLocation(otherFragment.access)).toBeUndefined();
    expect(takeQrTokenFromLocation(emptyToken.access)).toBeUndefined();
    expect(otherFragment.replaceState).toHaveBeenCalledOnce();
    expect(emptyToken.replaceState).toHaveBeenCalledOnce();
  });
});
