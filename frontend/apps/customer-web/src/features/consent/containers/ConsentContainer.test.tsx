import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { CustomerApiError, type CustomerFlowApi } from '../../customer-flow';
import { FixtureCustomerFlowApi } from '../../customer-flow/fixture';
import { FIXTURE_OTP } from '../../customer-flow/api/fixtureCustomerFlowData';
import { DESIGN_PLAN_ANSWERS } from '../../../testing/customerFlowTestData';
import { prepareFixtureWithAnswers, renderCustomerFlow } from '../../../testing/renderCustomerFlow';

const CONSENT_STEP = { step: 'consent', answers: DESIGN_PLAN_ANSWERS } as const;
const ONE_MINUTE_IN_MILLISECONDS = 60_000;

// Renders C9 on a fixture past C2 and C3; `now` moves the fixture's clock (the resend wait).
async function renderConsent(customerFlowApi?: FixtureCustomerFlowApi) {
  const fixture = customerFlowApi ?? (await prepareFixtureWithAnswers());
  return {
    fixture,
    ...renderCustomerFlow({ customerFlowApi: fixture, initialFlowState: CONSENT_STEP }),
  };
}

// Builds a fixture whose clock runs a minute behind, so a new OTP may be asked for at once.
async function fixtureWithResendAllowed(): Promise<FixtureCustomerFlowApi> {
  const fixture = new FixtureCustomerFlowApi({
    now: () => Date.now() - ONE_MINUTE_IN_MILLISECONDS,
  });
  await fixture.startSession('preparation-qr-token');
  await fixture.confirmBudget(300000);
  await fixture.answerComfortCheck(true);
  return fixture;
}

// Types an OTP into the six boxes (pasting fills them all, as PinInput allows).
async function typeOtp(otp: string) {
  const firstBox = screen.getByRole('textbox', { name: 'Digit 1 of 6' });
  await userEvent.click(firstBox);
  await userEvent.paste(otp);
}

afterEach(() => {
  window.localStorage.clear();
});

describe('C9 consent and OTP', () => {
  it('summarises the plan and asks for the OTP before Confirm opens', async () => {
    const { container } = await renderConsent();

    expect(
      await screen.findByRole('heading', { name: 'Check and confirm your plan' }),
    ).toBeTruthy();
    const summary = within(screen.getByRole('region', { name: 'Your plan' }));
    expect(summary.getByText('₹3,667')).toBeTruthy();
    expect(summary.getByText('₹0')).toBeTruthy();
    expect(summary.getByText('6 months')).toBeTruthy();
    expect(summary.getByText('₹22,000')).toBeTruthy();
    expect(screen.getByText('You can cancel within the cooling-off period.')).toBeTruthy();
    expect(screen.getByText(/We never ask for card details here\./)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Confirm' })).toHaveProperty('disabled', true);
    await expectNoAccessibilityViolations(container);
  });

  it('sends the OTP, shows the phone ending and the resend wait, then records consent', async () => {
    const { fixture, container } = await renderConsent();
    // Spied through the port, whose giveConsent also takes the language.
    const giveConsent = vi.spyOn(fixture as CustomerFlowApi, 'giveConsent');

    await userEvent.click(await screen.findByRole('button', { name: 'Send OTP' }));

    expect(
      screen.getByRole('group', { name: 'Enter the 6-digit OTP sent to your phone ending 42' }),
    ).toBeTruthy();
    expect(screen.getByText(/You can ask for a new OTP in 0:(30|29)/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Send a new OTP' })).toBeNull();
    await expectNoAccessibilityViolations(container);
    await typeOtp(FIXTURE_OTP);
    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));

    expect(await screen.findByRole('heading', { name: 'Your plan is ready' })).toBeTruthy();
    const [submission, idempotencyKey, language] = giveConsent.mock.calls[0] ?? [];
    expect(submission).toEqual({
      offerId: 'mock-offer-no-cost-6m',
      shownMonthlyInstallmentInPaise: 366667,
      shownTotalPayableInPaise: 2200000,
      otp: FIXTURE_OTP,
    });
    expect(idempotencyKey).toMatch(/^[0-9a-f-]{36}$/);
    expect(language).toBe('en');
  });

  it('says calmly how many tries are left after a wrong OTP, then expires it after the third', async () => {
    await renderConsent();
    await userEvent.click(await screen.findByRole('button', { name: 'Send OTP' }));

    await typeOtp('000000');
    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    expect((await screen.findByRole('alert')).textContent).toBe(
      'That OTP does not match. Check the message and try again. 2 tries left.',
    );
    await typeOtp('111111');
    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    expect(await screen.findByText(/1 try left\./)).toBeTruthy();
    await typeOtp('222222');
    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));

    expect(await screen.findByText('This OTP has expired. Ask for a new one.')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Confirm' })).toHaveProperty('disabled', true);
    expect(screen.queryByText(/locked|blocked|too many/i)).toBeNull();
  });

  it('offers a new OTP once the wait is over, and accepts the new one', async () => {
    await renderConsent(await fixtureWithResendAllowed());
    await userEvent.click(await screen.findByRole('button', { name: 'Send OTP' }));

    await userEvent.click(screen.getByRole('button', { name: 'Send a new OTP' }));
    await typeOtp(FIXTURE_OTP);
    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));

    expect(await screen.findByRole('heading', { name: 'Your plan is ready' })).toBeTruthy();
  });

  it('shows the wait when the server says a new OTP is too soon (429 with Retry-After)', async () => {
    const fixture = await prepareFixtureWithAnswers();
    vi.spyOn(fixture, 'requestConsentOtp').mockRejectedValue(
      new CustomerApiError(429, 'RATE_LIMITED', { hasProblemBody: true, retryAfterInSeconds: 24 }),
    );
    await renderConsent(fixture);

    await userEvent.click(await screen.findByRole('button', { name: 'Send OTP' }));

    expect(await screen.findByText(/You can ask for a new OTP in 0:2[34]/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Send OTP' })).toHaveProperty('disabled', true);
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('shows a calm message when the OTP could not be sent', async () => {
    const fixture = await prepareFixtureWithAnswers();
    vi.spyOn(fixture, 'requestConsentOtp').mockRejectedValueOnce(
      new CustomerApiError(0, 'NETWORK_UNAVAILABLE'),
    );
    await renderConsent(fixture);

    await userEvent.click(await screen.findByRole('button', { name: 'Send OTP' }));

    expect((await screen.findByRole('alert')).textContent).toContain(
      'Your phone could not reach us.',
    );
  });

  it('re-shows the plans with a notice when the plan shown has changed', async () => {
    const fixture = await prepareFixtureWithAnswers();
    vi.spyOn(fixture, 'giveConsent').mockRejectedValue(
      new CustomerApiError(409, 'SHOWN_PLAN_CHANGED', { hasProblemBody: true }),
    );
    await renderConsent(fixture);
    await userEvent.click(await screen.findByRole('button', { name: 'Send OTP' }));
    await typeOtp(FIXTURE_OTP);

    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));

    expect(await screen.findByRole('heading', { name: 'Your EMI options' })).toBeTruthy();
    expect(screen.getByText(/A plan’s figures changed\./)).toBeTruthy();
  });

  it('opens the receipt when consent was already given, and shows other failures calmly', async () => {
    const fixture = await prepareFixtureWithAnswers();
    vi.spyOn(fixture, 'giveConsent')
      .mockRejectedValueOnce(
        new CustomerApiError(503, 'SERVICE_UNAVAILABLE', { hasProblemBody: true }),
      )
      .mockRejectedValueOnce(
        new CustomerApiError(409, 'CONSENT_ALREADY_GIVEN', { hasProblemBody: true }),
      );
    vi.spyOn(fixture, 'getReceipt').mockReturnValue(new Promise(() => undefined));
    await renderConsent(fixture);
    await userEvent.click(await screen.findByRole('button', { name: 'Send OTP' }));
    await typeOtp(FIXTURE_OTP);

    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    expect((await screen.findByRole('alert')).textContent).toBe(
      'Something did not load. Please try again.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Confirm' }));

    expect(await screen.findByRole('status', { name: 'Getting your receipt' })).toBeTruthy();
  });

  it('records consent in Tamil when the customer reads C9 in Tamil', async () => {
    window.localStorage.setItem('emiCopilot.language', 'ta');
    const fixture = await prepareFixtureWithAnswers();
    const giveConsent = vi.spyOn(fixture as CustomerFlowApi, 'giveConsent');
    await renderConsent(fixture);

    await userEvent.click(await screen.findByRole('button', { name: 'OTP அனுப்பு' }));
    await userEvent.click(screen.getByRole('textbox', { name: 'இலக்கம் 1 / 6' }));
    await userEvent.paste(FIXTURE_OTP);
    await userEvent.click(screen.getByRole('button', { name: 'உறுதிசெய்' }));

    expect(await screen.findByRole('heading', { name: 'உங்கள் திட்டம் தயார்' })).toBeTruthy();
    expect(giveConsent.mock.calls[0]?.[2]).toBe('ta');
  });

  it('reads in Tamil and goes back to the explanation', async () => {
    window.localStorage.setItem('emiCopilot.language', 'ta');
    await renderConsent();

    expect(
      await screen.findByRole('heading', {
        name: 'உங்கள் திட்டத்தைச் சரிபார்த்து உறுதிசெய்யுங்கள்',
      }),
    ).toBeTruthy();
    expect(screen.getByText('குறிப்பிட்ட காலத்திற்குள் இதை ரத்து செய்யலாம்.')).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: 'பின் செல்' }));

    expect(
      screen.getByRole('heading', { name: 'உங்கள் திட்டம், எளிய வார்த்தைகளில்' }),
    ).toBeTruthy();
  });
});
