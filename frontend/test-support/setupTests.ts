// Unmounts every rendered tree after each test so tests never share DOM state.
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

beforeEach(() => {
  // jsdom has no canvas. Without this stub axe's colour-contrast probe prints a warning per test;
  // with it axe reports contrast as "incomplete". Contrast is guaranteed by the token pairs instead.
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
});

afterEach(() => {
  cleanup();
});
