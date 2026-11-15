import { useMutation } from '@tanstack/react-query';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { renderCustomerApp } from '../../../testing/renderCustomerApp';
import { CustomerApiError } from '../api/customerApiError';
import { FixtureCustomerFlowApi } from '../api/FixtureCustomerFlowApi';
import { useCustomerFlow } from '../hooks/useCustomerFlow';
import { useCustomerFlowApi } from '../hooks/useCustomerFlowApi';

// Shows the open session's shop and a button whose call fails because the session is gone.
function SessionProbe() {
  const { session, state } = useCustomerFlow();
  const customerFlowApi = useCustomerFlowApi();
  const failingCall = useMutation({ mutationFn: () => customerFlowApi.getReceipt() });
  return (
    <div>
      <p>{`${session.shopName} ${state.step}`}</p>
      <button
        type="button"
        onClick={() => {
          failingCall.mutate();
        }}
      >
        Call with a lost session
      </button>
    </div>
  );
}

afterEach(() => {
  window.localStorage.clear();
});

describe('CustomerSessionGate', () => {
  it('opens the session from the QR and shows the flow', async () => {
    const { container } = renderCustomerApp({ children: <SessionProbe /> });

    expect(await screen.findByText('Ravi Electronics welcome')).toBeTruthy();
    await expectNoAccessibilityViolations(container);
  });

  it('shows a skeleton while the session opens', () => {
    const customerFlowApi = new FixtureCustomerFlowApi();
    vi.spyOn(customerFlowApi, 'startSession').mockReturnValue(new Promise(() => undefined));

    renderCustomerApp({ children: <SessionProbe />, customerFlowApi });

    expect(screen.getByRole('status', { name: 'Opening your EMI options…' })).toBeTruthy();
  });

  it('asks for a new QR when the page has no token, without calling the server', async () => {
    const customerFlowApi = new FixtureCustomerFlowApi();
    const startSession = vi.spyOn(customerFlowApi, 'startSession');

    const { container } = renderCustomerApp({
      children: <SessionProbe />,
      customerFlowApi,
      qrToken: null,
    });

    expect(screen.getByRole('heading', { name: 'Ask the shop for a new QR' })).toBeTruthy();
    expect(startSession).not.toHaveBeenCalled();
    await expectNoAccessibilityViolations(container);
  });

  it('asks for a new QR when the QR was already used', async () => {
    const customerFlowApi = new FixtureCustomerFlowApi();
    await customerFlowApi.startSession('used-qr');

    renderCustomerApp({ children: <SessionProbe />, customerFlowApi, qrToken: 'used-qr' });

    expect(await screen.findByRole('heading', { name: 'Ask the shop for a new QR' })).toBeTruthy();
  });

  it('offers a calm retry when the network failed, then opens the session', async () => {
    const customerFlowApi = new FixtureCustomerFlowApi();
    vi.spyOn(customerFlowApi, 'startSession').mockRejectedValueOnce(
      new CustomerApiError(0, 'NETWORK_UNAVAILABLE'),
    );
    renderCustomerApp({ children: <SessionProbe />, customerFlowApi });

    expect(await screen.findByRole('alert')).toHaveProperty(
      'textContent',
      'Your phone could not reach us. Check your internet and try again.Try again',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('Ravi Electronics welcome')).toBeTruthy();
  });

  it('ends on the session screen when a later call finds the session gone', async () => {
    const customerFlowApi = new FixtureCustomerFlowApi();
    vi.spyOn(customerFlowApi, 'getReceipt').mockRejectedValue(
      new CustomerApiError(401, 'CUSTOMER_SESSION_TOKEN_INVALID', { hasProblemBody: true }),
    );
    renderCustomerApp({ children: <SessionProbe />, customerFlowApi });

    await userEvent.click(await screen.findByRole('button', { name: 'Call with a lost session' }));

    expect(await screen.findByText('Ravi Electronics sessionUnavailable')).toBeTruthy();
  });
});
