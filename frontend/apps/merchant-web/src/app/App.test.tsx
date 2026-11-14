import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { initializeMerchantI18n } from '../i18n/initializeMerchantI18n';
import { App } from './App';
import { createMerchantQueryClient } from './createMerchantQueryClient';
import { MERCHANT_ROUTES } from './merchantRoutes';

// Renders the whole merchant app at a path, with fresh translations and cache.
function renderMerchantApp(path = '/') {
  return render(
    <App
      i18n={initializeMerchantI18n()}
      queryClient={createMerchantQueryClient()}
      router={createMemoryRouter(MERCHANT_ROUTES, { initialEntries: [path] })}
    />,
  );
}

afterEach(() => {
  window.localStorage.clear();
});

describe('merchant app shell', () => {
  it('renders the brand panel in English by default', () => {
    renderMerchantApp();

    expect(screen.getByRole('heading', { level: 1, name: 'EMI Copilot' })).toBeTruthy();
    expect(screen.getByText('Help customers pick an EMI they understand.')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'EN' }).getAttribute('aria-pressed')).toBe('true');
  });

  it('switches the shop language to Tamil and remembers it', async () => {
    renderMerchantApp('/any/path');

    await userEvent.click(screen.getByRole('button', { name: 'தமிழ்' }));

    expect(
      screen.getByText('வாடிக்கையாளர்கள் புரிந்துகொள்ளும் EMI-யைத் தேர்ந்தெடுக்க உதவுங்கள்.'),
    ).toBeTruthy();
    expect(screen.getByRole('group', { name: 'மொழி' })).toBeTruthy();
    expect(window.localStorage.getItem('emiCopilot.language')).toBe('ta');
  });

  it('has no accessibility violations', async () => {
    const { container } = renderMerchantApp();

    await expectNoAccessibilityViolations(container);
  });
});
