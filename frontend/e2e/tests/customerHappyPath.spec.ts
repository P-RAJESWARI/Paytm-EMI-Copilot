// The customer happy path on a phone (360 x 800), in English, against the real backend: scan the
// counter tablet's QR, tell a budget, allow the comfort check, compare the three design plans, look
// at the alternatives, read the explanation, consent with the Mock OTP (after one wrong try) and
// reach the handoff, while the tablet's M3 turns to "Ready to pay" live.
import { expect, test, type Page } from '@playwright/test';

import { expectNoAccessibilityViolations } from '../support/accessibility';
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
import {
  DEMO_PRODUCT_NAME,
  openCounterTablet,
  startSaleOnTheTablet,
} from '../support/customerSales';
import { ENGLISH_CUSTOMER_WORDS as WORDS } from '../support/customerWords';
import { MOCK_CONSENT_OTP_CODE } from '../support/endToEndSettings';
import { expectNoCustomerPrivateWords, pairThisDevice } from '../support/merchantScreens';

// C4: the three design plans in the server's order (cardless first: the only one within ₹3,000),
// each with its monthly amount and extra in total, its band and its total.
async function expectDesignPlansRanked(page: Page) {
  const cardless = planCards(page).nth(0);
  const noCost = planCards(page).nth(1);
  const card = planCards(page).nth(2);
  await expect(cardless).toContainText('Demo cardless lender (Mock), 12 months');
  await expect(cardless).toContainText('Each month₹2,050for 12 months');
  await expect(cardless).toContainText('Extra in total₹2,600');
  await expect(cardless).toContainText(WORDS.bandWords.comfortable);
  await expect(noCost).toContainText('No-cost EMI');
  await expect(noCost).toContainText('Each month₹3,667for 6 months');
  await expect(noCost).toContainText('Extra in total₹0on top of ₹22,000');
  await expect(noCost).toContainText(WORDS.bandWords.stretching);
  await expect(noCost).toContainText('You pay in all ₹22,000');
  await expect(card).toContainText("Your card's bank, 6 months");
  await expect(card).toContainText('Each month₹3,850');
  await expect(card).toContainText('Extra in total₹1,100');
  await expect(card).toContainText(WORDS.bandWords.stretching);
  await expect(page.getByText(WORDS.bandWords.risky)).toHaveCount(0);
}

// C6: the ₹4,000 down payment and the cheaper 64 GB model both bring the plan to ₹3,000 a month
// (Stretching, 36.7%), and both need the shop's help (ADR 0022 decision 1).
async function expectAlternativesNeedTheShop(page: Page) {
  const options = page.getByRole('group', { name: 'Ways to try' });
  await expect(options.getByRole('button', { name: 'Longer tenure' })).toBeVisible();
  await options.getByRole('button', { name: 'Add a ₹4,000 down payment' }).click();
  const downPayment = page.getByRole('region', { name: 'No-cost EMI, 6 months, ₹4,000 down' });
  await expect(downPayment).toContainText('Each month₹3,000Was ₹3,667');
  await expect(downPayment).toContainText(`${WORDS.bandWords.stretching} 36.7%`);
  await expect(downPayment).toContainText('Ask the shop to set this up');
  await checkCustomerScreen(page, 'C6 alternatives, down payment', WORDS);

  await options.getByRole('button', { name: 'Cheaper model' }).click();
  const cheaperModel = page.getByRole('region', { name: 'Example phone, 64 GB, ₹18,000' });
  await expect(cheaperModel).toContainText('Each month₹3,000Was ₹3,667');
  await expect(cheaperModel).toContainText('36.7%');
  await expect(cheaperModel).toContainText(
    'The shop starts a new sale for this model and shows you a new QR.',
  );
  await expect(cheaperModel.getByRole('button')).toHaveCount(0);
  await checkCustomerScreen(page, 'C6 alternatives, cheaper model', WORDS);
}

test('a customer agrees to the no-cost plan on their phone and the tablet sees "Ready to pay" live', async ({
  page,
  browser,
}) => {
  const { merchantContext, merchantPage } = await openCounterTablet(browser);
  try {
    await pairThisDevice(merchantPage);
    const { customerUrl } = await startSaleOnTheTablet(merchantPage);
    const merchantStatus = merchantPage.getByRole('region', {
      name: 'The customer is choosing a plan on their phone',
    });
    await expect(merchantStatus).toContainText('Choosing');

    await test.step('C1 opens from the QR link with the shop, item and price', async () => {
      await openCustomerQrLink(page, customerUrl);
      await expect(page.getByText('At Ravi Electronics')).toBeVisible();
      await expect(page.getByText(DEMO_PRODUCT_NAME)).toBeVisible();
      await expect(page.getByText('₹22,000')).toBeVisible();
      await checkCustomerScreen(page, 'C1 welcome', WORDS);
      await chooseLanguageAndStart(page, WORDS);
    });

    await test.step('C2 takes ₹3,000 a month and asks to confirm it', async () => {
      await typeMonthlyBudget(page, WORDS, '3000');
      await checkCustomerScreen(page, 'C2 budget, confirm line', WORDS);
      await confirmMonthlyBudget(page, WORDS);
    });

    await test.step('C3 says the shop cannot see the comfort check, and the customer allows it', async () => {
      await expect(page.getByText('The shop cannot see this information.')).toBeVisible();
      await expect(
        page.getByText('This is advice to help you choose. It is not a loan decision.'),
      ).toBeVisible();
      await checkCustomerScreen(page, 'C3 comfort check consent', WORDS);
      await answerComfortCheck(page, WORDS, 'allow');
    });

    await test.step('C4 compares the three design plans with bands, cardless first', async () => {
      await expectDesignPlansRanked(page);
      await checkCustomerScreen(page, 'C4 plans', WORDS);
      // The customer told a budget and ran the comfort check; the tablet still shows none of it.
      await expectNoCustomerPrivateWords(merchantPage, 'M3 while the customer compares plans');
      await chooseNoCostPlan(page, WORDS);
    });

    await test.step('C6 shows ₹3,000 a month alternatives that need the shop', async () => {
      await expect(page.getByRole('region', { name: 'Plan you are looking at' })).toContainText(
        'No-cost EMI, 6 months',
      );
      await expectAlternativesNeedTheShop(page);
      await keepPlanAndReadExplanation(page, WORDS);
    });

    await test.step('C7 explains the plan with ₹3,667 a month and ₹0 extra', async () => {
      await expect(explanationText(page, WORDS)).toContainText('₹3,667');
      await expect(explanationText(page, WORDS)).toContainText('₹0');
      await expect(
        page.getByRole('list', { name: 'The two numbers to remember' }).getByRole('listitem'),
      ).toHaveText(['₹3,667 a month', '₹0 extra in total']);
      await checkCustomerScreen(page, 'C7 explanation', WORDS);
    });

    await test.step('C9 sends the OTP to the phone ending 42 and calmly counts a wrong try', async () => {
      await continueToConsentAndSendOtp(page, WORDS);
      const summary = page.getByRole('region', { name: WORDS.planSummaryHeading });
      await expect(summary).toContainText('₹3,667');
      await expect(summary).toContainText('₹22,000');
      await checkCustomerScreen(page, 'C9 consent with the OTP sent', WORDS);
      await enterOtpAndConfirm(page, WORDS, '000000');
      await expect(page.getByRole('alert')).toHaveText(WORDS.wrongOtpWithTwoTriesLeft);
      await checkCustomerScreen(page, 'C9 consent after a wrong OTP', WORDS);
      await enterOtpAndConfirm(page, WORDS, MOCK_CONSENT_OTP_CODE);
    });

    await test.step('C10 hands off to the shop with an EMI- reference', async () => {
      await expectHandoffWithReference(page, WORDS);
      await checkCustomerScreen(page, 'C10 handoff', WORDS);
    });

    await test.step('M3 turns to "Ready to pay" live with the agreed plan', async () => {
      const agreedPlan = merchantPage.getByRole('region', {
        name: 'The customer agreed to a plan',
      });
      await expect(agreedPlan).toContainText('Ready to pay');
      await expect(agreedPlan).toContainText('No-cost EMI, 6 months');
      await expect(agreedPlan).toContainText('Each month₹3,667');
      await expect(agreedPlan).toContainText('Extra in total₹0');
      await expect(agreedPlan).toContainText('Total₹22,000');
      await expectNoCustomerPrivateWords(merchantPage, 'M3 ready to pay after customer consent');
      await expectNoAccessibilityViolations(merchantPage, 'M3 ready to pay after customer consent');
    });
  } finally {
    await merchantContext.close();
  }
});
