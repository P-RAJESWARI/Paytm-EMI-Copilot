import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { FIXTURE_OTP } from '../features/customer-flow/api/fixtureCustomerFlowData';
import { renderCustomerFlow } from '../testing/renderCustomerFlow';

/** The visible words of each step of the happy path, in one language. */
interface JourneyWords {
  tamilOrEnglishChoice: string;
  start: string;
  amountLabel: string;
  continueLabel: string;
  confirmBudget: string;
  allow: string;
  noCostPlanRadio: string;
  continueToConfirm: string;
  sendOtp: string;
  firstOtpDigit: string;
  confirm: string;
  handoffTitle: string;
}

const ENGLISH_WORDS: JourneyWords = {
  tamilOrEnglishChoice: 'English',
  start: 'Start',
  amountLabel: 'Monthly amount',
  continueLabel: 'Continue',
  confirmBudget: 'Yes, correct',
  allow: 'Allow',
  noCostPlanRadio: 'No-cost EMI Brand, 6 months',
  continueToConfirm: 'Continue to confirm',
  sendOtp: 'Send OTP',
  firstOtpDigit: 'Digit 1 of 6',
  confirm: 'Confirm',
  handoffTitle: 'Your plan is ready',
};

const TAMIL_WORDS: JourneyWords = {
  tamilOrEnglishChoice: 'தமிழ்',
  start: 'தொடங்கு',
  amountLabel: 'மாதத் தொகை',
  continueLabel: 'தொடர்க',
  confirmBudget: 'ஆம், சரி',
  allow: 'அனுமதி',
  noCostPlanRadio: 'கட்டணமில்லா EMI Brand, 6 மாதங்கள்',
  continueToConfirm: 'உறுதிசெய்யத் தொடர்க',
  sendOtp: 'OTP அனுப்பு',
  firstOtpDigit: 'இலக்கம் 1 / 6',
  confirm: 'உறுதிசெய்',
  handoffTitle: 'உங்கள் திட்டம் தயார்',
};

// Walks C1, C2, C3, C4, C6, C7, C9 and C10 with the design answers in one language.
async function walkTheHappyPath(words: JourneyWords) {
  const languageChoice = await screen.findByRole('group', { name: 'Choose your language' });
  const choice = Array.from(languageChoice.querySelectorAll('button')).find(
    (button) => button.textContent === words.tamilOrEnglishChoice,
  );
  if (choice === undefined) throw new Error('Language choice missing');
  await userEvent.click(choice);
  await userEvent.click(screen.getByRole('button', { name: words.start }));
  await userEvent.type(screen.getByRole('textbox', { name: words.amountLabel }), '3000');
  await userEvent.click(screen.getByRole('button', { name: words.continueLabel }));
  await userEvent.click(screen.getByRole('button', { name: words.confirmBudget }));
  await userEvent.click(await screen.findByRole('button', { name: words.allow }));
  await userEvent.click(await screen.findByRole('radio', { name: words.noCostPlanRadio }));
  await userEvent.click(screen.getByRole('button', { name: words.continueLabel }));
  await screen.findAllByRole('button', { pressed: false });
  await userEvent.click(screen.getByRole('button', { name: words.continueLabel }));
  await userEvent.click(await screen.findByRole('button', { name: words.continueToConfirm }));
  await userEvent.click(await screen.findByRole('button', { name: words.sendOtp }));
  await userEvent.click(screen.getByRole('textbox', { name: words.firstOtpDigit }));
  await userEvent.paste(FIXTURE_OTP);
  await userEvent.click(screen.getByRole('button', { name: words.confirm }));
}

afterEach(() => {
  window.localStorage.clear();
});

describe('customer flow happy path (fixture API)', () => {
  it('reaches the handoff in English', async () => {
    renderCustomerFlow();

    await walkTheHappyPath(ENGLISH_WORDS);

    expect(await screen.findByRole('heading', { name: ENGLISH_WORDS.handoffTitle })).toBeTruthy();
    expect(screen.getByText('EMI-2611-0042')).toBeTruthy();
  });

  it('reaches the handoff in Tamil, chosen on C1 and kept to the receipt', async () => {
    renderCustomerFlow();

    await walkTheHappyPath(TAMIL_WORDS);

    expect(await screen.findByRole('heading', { name: TAMIL_WORDS.handoffTitle })).toBeTruthy();
    expect(document.documentElement.lang).toBe('ta');
  });
});
