// The customer's main path on a phone with Tamil chosen on C1: every screen to the handoff stays in
// Tamil (no raw keys, no English interface words), and the language carries to the receipt.
import { expect, test } from '@playwright/test';

import {
  answerComfortCheck,
  checkCustomerScreen,
  chooseLanguageAndStart,
  chooseNoCostPlan,
  confirmMonthlyBudget,
  continueToConsentAndSendOtp,
  enterOtpAndConfirm,
  expectHandoffWithReference,
  explanationText,
  keepPlanAndReadExplanation,
  openCustomerQrLink,
  planCards,
  typeMonthlyBudget,
} from '../support/customerScreens';
import { startSaleThroughApi } from '../support/customerSales';
import { TAMIL_CUSTOMER_WORDS as WORDS } from '../support/customerWords';
import { MOCK_CONSENT_OTP_CODE } from '../support/endToEndSettings';
import { pairDeviceThroughApi } from '../support/mockCustomerSimulator';

test('a customer who chooses Tamil on C1 reads every screen in Tamil, through to the receipt', async ({
  page,
  request,
}) => {
  const { customerUrl } = await startSaleThroughApi(request, await pairDeviceThroughApi(request));

  await openCustomerQrLink(page, customerUrl);
  await chooseLanguageAndStart(page, WORDS);

  await test.step('C2 and C3 in Tamil', async () => {
    await typeMonthlyBudget(page, WORDS, '3000');
    await checkCustomerScreen(page, 'C2 budget in Tamil', WORDS);
    await confirmMonthlyBudget(page, WORDS);
    await checkCustomerScreen(page, 'C3 comfort check consent in Tamil', WORDS);
    await answerComfortCheck(page, WORDS, 'allow');
  });

  await test.step('C4 shows the plans with Tamil band words', async () => {
    await expect(planCards(page).nth(0)).toContainText(WORDS.bandWords.comfortable);
    await expect(planCards(page).nth(1)).toContainText('₹3,667');
    await expect(planCards(page).nth(1)).toContainText(WORDS.bandWords.stretching);
    await checkCustomerScreen(page, 'C4 plans in Tamil', WORDS);
    await chooseNoCostPlan(page, WORDS);
    await checkCustomerScreen(page, 'C6 alternatives in Tamil', WORDS);
  });

  await test.step('C7 explains the plan in Tamil with its numbers', async () => {
    await keepPlanAndReadExplanation(page, WORDS);
    await expect(explanationText(page, WORDS)).toContainText('₹3,667');
    await checkCustomerScreen(page, 'C7 explanation in Tamil', WORDS);
  });

  await test.step('C9 consents in Tamil and C10 hands off in Tamil', async () => {
    await continueToConsentAndSendOtp(page, WORDS);
    await checkCustomerScreen(page, 'C9 consent in Tamil', WORDS);
    await enterOtpAndConfirm(page, WORDS, MOCK_CONSENT_OTP_CODE);
    await expectHandoffWithReference(page, WORDS);
    await checkCustomerScreen(page, 'C10 handoff in Tamil', WORDS);
  });
});
