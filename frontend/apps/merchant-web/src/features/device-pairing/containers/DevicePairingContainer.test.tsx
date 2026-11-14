import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import {
  jsonResponse,
  problemResponse,
  type FakeRouteHandler,
} from '../../../testing/fakeMerchantBackend';
import { TEST_MERCHANT_PROFILE } from '../../../testing/merchantTestData';
import { renderMerchantApp } from '../../../testing/renderMerchantApp';

// Renders M1 unpaired with the given pairing answer.
function renderPairingScreen(pairingHandler: FakeRouteHandler) {
  return renderMerchantApp({
    path: '/pair',
    session: null,
    routes: { 'POST /api/v1/merchants/pairing': pairingHandler },
  });
}

// Types a shop ID and PIN and presses "Pair device".
async function pairWith(shopId: string, pin: string) {
  await userEvent.type(screen.getByLabelText('Shop ID'), shopId);
  await userEvent.click(screen.getByLabelText('PIN digit 1 of 6'));
  await userEvent.keyboard(pin);
  await userEvent.click(screen.getByRole('button', { name: 'Pair device' }));
}

afterEach(() => {
  window.localStorage.clear();
});

describe('M1 device pairing', () => {
  it('pairs, keeps the token for the API and opens New EMI sale with the shop card', async () => {
    const { fakeBackend, router } = renderPairingScreen(() =>
      jsonResponse(
        {
          accessToken: 'new-token',
          tokenType: 'Bearer',
          expiresAt: '2026-11-15T22:00:00Z',
          merchant: TEST_MERCHANT_PROFILE,
        },
        201,
      ),
    );

    await pairWith(' RAVI-0193 ', '123456');

    expect(await screen.findByRole('navigation', { name: 'Main' })).toBeTruthy();
    expect(router.state.location.pathname).toBe('/sale');
    expect(
      fakeBackend.recordedRequests.find((request) => request.path === '/api/v1/merchants/pairing')
        ?.body,
    ).toEqual({
      shopId: 'RAVI-0193',
      pin: '123456',
    });
    await waitFor(() => {
      const profileRequest = fakeBackend.recordedRequests.find(
        (request) => request.path === '/api/v1/merchants/me',
      );
      expect(profileRequest?.headers.get('Authorization')).toBe('Bearer new-token');
    });
    expect(window.localStorage.getItem('emiCopilot.language')).not.toBe('new-token');
  });

  it('checks the fields before sending anything', async () => {
    const { fakeBackend } = renderPairingScreen(() => jsonResponse({}, 201));

    await userEvent.click(screen.getByRole('button', { name: 'Pair device' }));

    expect(await screen.findByText('Enter your shop ID.')).toBeTruthy();
    expect(screen.getByText('Enter all 6 digits of the PIN.')).toBeTruthy();
    await userEvent.type(screen.getByLabelText('Shop ID'), 'RAVI 0193');
    await userEvent.click(screen.getByRole('button', { name: 'Pair device' }));
    expect(
      await screen.findByText('A shop ID has letters, numbers and dashes, like RAVI-0193.'),
    ).toBeTruthy();
    expect(fakeBackend.recordedRequests.some((request) => request.method === 'POST')).toBe(false);
  });

  it('explains a wrong PIN calmly and empties the PIN boxes', async () => {
    renderPairingScreen(() => problemResponse(401, 'INVALID_PAIRING_CREDENTIALS'));

    await pairWith('RAVI-0193', '000000');

    expect(
      await screen.findByText(
        'That shop ID and PIN did not match. Please check both and try again.',
      ),
    ).toBeTruthy();
    expect(screen.getByLabelText<HTMLInputElement>('PIN digit 1 of 6').value).toBe('');
    expect(screen.queryByText(/English developer detail/)).toBeNull();
  });

  it('says how many minutes pairing is paused after repeated wrong PINs', async () => {
    renderPairingScreen(() =>
      problemResponse(429, 'PAIRING_TEMPORARILY_LOCKED', { 'Retry-After': '840' }),
    );

    await pairWith('RAVI-0193', '000000');

    expect(
      await screen.findByText(
        'Pairing is paused for this shop for about 14 minutes. The shop owner can help if you need it sooner.',
      ),
    ).toBeTruthy();
  });

  it('asks the device to wait when it sent too many requests', async () => {
    renderPairingScreen(() => problemResponse(429, 'RATE_LIMITED', { 'Retry-After': '30' }));

    await pairWith('RAVI-0193', '000000');

    expect(
      await screen.findByText(
        'This device has tried many times. Please wait about 1 minute and try again.',
      ),
    ).toBeTruthy();
  });

  it('falls back to the general wait message when no Retry-After came back', async () => {
    renderPairingScreen(() => problemResponse(429, 'RATE_LIMITED'));

    await pairWith('RAVI-0193', '000000');

    expect(
      await screen.findByText('Too many requests just now. Please wait a minute and try again.'),
    ).toBeTruthy();
  });

  it('explains a network failure and shows the pairing state while sending', async () => {
    let rejectPairing: (error: Error) => void = () => undefined;
    renderPairingScreen(
      () =>
        new Promise<Response>((_resolve, reject) => {
          rejectPairing = reject;
        }),
    );

    await pairWith('RAVI-0193', '123456');
    const pairingButton = await screen.findByRole('button', { name: 'Pairing…' });
    expect((pairingButton as HTMLButtonElement).disabled).toBe(true);
    rejectPairing(new TypeError('Failed to fetch'));

    expect(
      await screen.findByText(
        "Could not reach the server. Check the shop's internet connection and try again.",
      ),
    ).toBeTruthy();
  });

  it('shows M1 in Tamil with the owner note instead of an owner app', async () => {
    renderPairingScreen(() => jsonResponse({}, 201));

    await userEvent.click(screen.getByRole('button', { name: 'தமிழ்' }));

    expect(
      screen.getByRole('heading', { level: 1, name: 'இந்தச் சாதனத்தை இணைக்கவும்' }),
    ).toBeTruthy();
    expect(
      screen.getByText('PIN இல்லையா? இணைப்பு PIN-ஐக் கடை உரிமையாளரிடம் கேளுங்கள்.'),
    ).toBeTruthy();
  });

  it('has no accessibility violations, including the error state', async () => {
    const { container } = renderPairingScreen(() =>
      problemResponse(401, 'INVALID_PAIRING_CREDENTIALS'),
    );
    expect(screen.getByText('No PIN? Ask the shop owner for the pairing PIN.')).toBeTruthy();
    await expectNoAccessibilityViolations(container);

    await pairWith('RAVI-0193', '000000');
    await screen.findByRole('alert');

    await expectNoAccessibilityViolations(container);
  });
});
