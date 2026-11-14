import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { problemResponse } from '../testing/fakeMerchantBackend';
import { renderMerchantApp } from '../testing/renderMerchantApp';

afterEach(() => {
  window.localStorage.clear();
});

describe('merchant app shell', () => {
  it('sends an unpaired tablet to the pairing screen with the brand panel', () => {
    renderMerchantApp({ path: '/sale', session: null });

    expect(screen.getByRole('heading', { level: 1, name: 'Pair this device' })).toBeTruthy();
    expect(screen.getByText('Help customers pick an EMI they understand.')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'EN' }).getAttribute('aria-pressed')).toBe('true');
  });

  it('shows the two shop tabs and the shop card once paired', async () => {
    renderMerchantApp({ path: '/sale' });

    const navigation = screen.getByRole('navigation', { name: 'Main' });
    expect(screen.getByRole('link', { name: 'New EMI sale' }).getAttribute('aria-current')).toBe(
      'page',
    );
    expect(screen.getByRole('link', { name: 'Sales report' })).toBeTruthy();
    expect(navigation.textContent).toContain('Ravi Electronics');
    expect(await screen.findByText('Counter tablet 1')).toBeTruthy();
  });

  it('sends a paired tablet away from the pairing screen and unknown paths to New EMI sale', () => {
    const { router } = renderMerchantApp({ path: '/pair' });

    expect(router.state.location.pathname).toBe('/sale');
  });

  it('switches the shop language to Tamil from the sidebar and remembers it on this device', async () => {
    renderMerchantApp({ path: '/report' });

    await userEvent.click(screen.getByRole('button', { name: 'தமிழ்' }));

    expect(screen.getByRole('link', { name: 'புதிய EMI விற்பனை' })).toBeTruthy();
    expect(screen.getByRole('group', { name: 'மொழி' })).toBeTruthy();
    expect(window.localStorage.getItem('emiCopilot.language')).toBe('ta');
  });

  it('forgets the token and returns to pairing when the server says the token is no longer valid', async () => {
    const { router, queryClient } = renderMerchantApp({
      path: '/sale',
      routes: {
        'GET /api/v1/merchants/me': () => problemResponse(401, 'MERCHANT_AUTHENTICATION_REQUIRED'),
      },
    });

    expect(await screen.findByRole('heading', { level: 1, name: 'Pair this device' })).toBeTruthy();
    expect(router.state.location.pathname).toBe('/pair');
    await waitFor(() => {
      expect(queryClient.getQueryCache().getAll()).toEqual([]);
    });
  });

  it('has no accessibility violations on the paired shell', async () => {
    const { container } = renderMerchantApp({ path: '/sale' });
    await screen.findByText('Counter tablet 1');

    await expectNoAccessibilityViolations(container);
  });
});
