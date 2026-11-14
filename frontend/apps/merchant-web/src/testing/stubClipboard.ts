import { afterEach } from 'vitest';

// Puts a fake navigator.clipboard in place for one test (jsdom has none) and removes it after.
export function stubClipboard(clipboard: Pick<Clipboard, 'writeText'> | undefined): void {
  Object.defineProperty(navigator, 'clipboard', { value: clipboard, configurable: true });
}

afterEach(() => {
  Reflect.deleteProperty(navigator, 'clipboard');
});
