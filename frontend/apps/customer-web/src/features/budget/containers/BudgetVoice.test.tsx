import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { CustomerApiError } from '../../customer-flow';
import { FixtureCustomerFlowApi } from '../../customer-flow/fixture';
import { installFakeMicrophone, removeFakeMicrophone } from '../../../testing/fakeMicrophone';
import { renderCustomerFlow } from '../../../testing/renderCustomerFlow';

const BUDGET_STEP = { step: 'budget', previousBudgetInPaise: undefined } as const;

afterEach(() => {
  removeFakeMicrophone();
  window.localStorage.clear();
});

// Taps the microphone, then taps again to stop, as the customer does on C2.
async function sayAmountIntoMicrophone(): Promise<void> {
  await userEvent.click(await screen.findByRole('button', { name: 'Tap and say the amount' }));
  await userEvent.click(await screen.findByRole('button', { name: 'Listening. Tap to stop.' }));
}

describe('C2 budget by voice', () => {
  it('prefills the heard amount and asks "Correct?"; only the tap sends the budget', async () => {
    const microphone = installFakeMicrophone();
    const customerFlowApi = new FixtureCustomerFlowApi();
    const transcribeSpeech = vi.spyOn(customerFlowApi, 'transcribeSpeech');
    const confirmBudget = vi.spyOn(customerFlowApi, 'confirmBudget');
    const { container } = renderCustomerFlow({ customerFlowApi, initialFlowState: BUDGET_STEP });

    await sayAmountIntoMicrophone();

    expect(await screen.findByText('You said ₹3,000. Correct?')).toBeTruthy();
    expect(screen.getByRole('textbox', { name: 'Monthly amount' })).toHaveProperty('value', '3000');
    expect(transcribeSpeech).toHaveBeenCalledWith(expect.any(Blob), 'BUDGET', 'en');
    expect(confirmBudget).not.toHaveBeenCalled();
    expect(microphone.stoppedTrackCount()).toBe(1);
    await expectNoAccessibilityViolations(container);

    await userEvent.click(screen.getByRole('button', { name: 'Yes, correct' }));
    expect(confirmBudget).toHaveBeenCalledWith(300000);
  });

  it('shows the misheard state with the heard amount to fix or say again', async () => {
    installFakeMicrophone();
    const customerFlowApi = new FixtureCustomerFlowApi();
    vi.spyOn(customerFlowApi, 'transcribeSpeech').mockResolvedValue({
      transcript: 'thirty thousand',
      recognisedAmountInPaise: 3000000,
      isLikelyMisheard: true,
    });
    const { container } = renderCustomerFlow({ customerFlowApi, initialFlowState: BUDGET_STEP });

    await sayAmountIntoMicrophone();

    expect(await screen.findByText('We heard ₹30,000.')).toBeTruthy();
    expect(
      screen.getByText('If that is wrong, tap the amount above and type the right number.'),
    ).toBeTruthy();
    expect(screen.getByRole('textbox', { name: 'Monthly amount' })).toHaveProperty(
      'value',
      '30000',
    );
    expect(screen.queryByText(/Correct\?/)).toBeNull();
    expect(screen.getByRole('button', { name: 'Say it again' })).toBeTruthy();
    await expectNoAccessibilityViolations(container);

    await userEvent.type(screen.getByRole('textbox', { name: 'Monthly amount' }), '{Backspace}');
    expect(screen.queryByText('We heard ₹30,000.')).toBeNull();
  });

  it('says no amount was caught when the transcript has none', async () => {
    installFakeMicrophone();
    const customerFlowApi = new FixtureCustomerFlowApi();
    vi.spyOn(customerFlowApi, 'transcribeSpeech').mockResolvedValue({
      transcript: 'hello',
      recognisedAmountInPaise: null,
      isLikelyMisheard: false,
    });
    renderCustomerFlow({ customerFlowApi, initialFlowState: BUDGET_STEP });

    await sayAmountIntoMicrophone();

    expect(await screen.findByText('We did not catch an amount.')).toBeTruthy();
    expect(screen.getByRole('textbox', { name: 'Monthly amount' })).toHaveProperty('value', '');
  });

  it('asks quietly to type instead when the microphone is refused', async () => {
    installFakeMicrophone(new DOMException('Permission denied', 'NotAllowedError'));
    const { container } = renderCustomerFlow({ initialFlowState: BUDGET_STEP });

    await userEvent.click(await screen.findByRole('button', { name: 'Tap and say the amount' }));

    expect(
      await screen.findByText('Voice is not working right now. Please type the amount.'),
    ).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
    await expectNoAccessibilityViolations(container);
  });

  it('asks quietly to type instead when speech is unavailable on the server', async () => {
    installFakeMicrophone();
    const customerFlowApi = new FixtureCustomerFlowApi();
    vi.spyOn(customerFlowApi, 'transcribeSpeech').mockRejectedValue(
      new CustomerApiError(502, 'SPEECH_UNAVAILABLE', { hasProblemBody: true }),
    );
    renderCustomerFlow({ customerFlowApi, initialFlowState: BUDGET_STEP });

    await sayAmountIntoMicrophone();

    expect(
      await screen.findByText('Voice is not working right now. Please type the amount.'),
    ).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('hides the microphone when voice is off for this session', async () => {
    installFakeMicrophone();
    const customerFlowApi = new FixtureCustomerFlowApi();
    const startSession = customerFlowApi.startSession.bind(customerFlowApi);
    vi.spyOn(customerFlowApi, 'startSession').mockImplementation(async (qrToken) => ({
      ...(await startSession(qrToken)),
      isVoiceAvailable: false,
    }));
    renderCustomerFlow({ customerFlowApi, initialFlowState: BUDGET_STEP });

    expect(await screen.findByText('Type an amount to continue.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Tap and say the amount' })).toBeNull();
  });
});
