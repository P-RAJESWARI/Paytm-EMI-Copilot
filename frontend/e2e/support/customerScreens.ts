// Steps and checks shared by the customer end-to-end tests on the phone (360 x 800): open a sale's
// QR link, walk C1 to C10 in English or Tamil, and check every screen (axe, width, translations).
import { expect, test, type Page } from '@playwright/test';

import { expectNoAccessibilityViolations } from './accessibility';
import { LANGUAGE_CHOICE_GROUP_NAME, type CustomerWords } from './customerWords';
import { expectNoHorizontalScroll } from './merchantScreens';

/** A customer translation key shown instead of its text, such as "plans.title", or a {{gap}}. */
const UNTRANSLATED_CUSTOMER_TEXT =
  /\b(?:common|language|comfortBand|flow|session|problems|welcome|budget|comfortConsent|comfortDetail|plan|plans|alternatives|explanation|consent|receipt)\.[A-Za-z]|\{\{/;

// Checks one customer screen: no axe violations, no sideways scrolling on the phone, no raw
// translation keys, and on a Tamil run the page language is Tamil with no English interface words.
export async function checkCustomerScreen(page: Page, screenName: string, words: CustomerWords) {
  await test.step(`${screenName} fits the phone, is translated and accessible`, async () => {
    await expect(page.locator('html')).toHaveAttribute('lang', words.language);
    const pageText = await page.locator('body').innerText();
    expect(pageText).not.toMatch(UNTRANSLATED_CUSTOMER_TEXT);
    if (words.otherLanguageInterfaceWords !== undefined) {
      expect(pageText).not.toMatch(words.otherLanguageInterfaceWords);
    }
    await expectNoHorizontalScroll(page);
  });
  await expectNoAccessibilityViolations(page, screenName);
}

// Opens the QR link as a phone camera would, waits for C1, and checks that the token has left the
// address bar (it lives only in page memory; frontend.md section 9).
export async function openCustomerQrLink(page: Page, customerUrl: string) {
  await test.step('open the QR link on the phone', async () => {
    await page.goto(customerUrl);
    await expect(page.getByRole('group', { name: LANGUAGE_CHOICE_GROUP_NAME })).toBeVisible();
    expect(new URL(page.url()).hash).toBe('');
    expect(page.url()).not.toContain('t=');
  });
}

// C1: chooses the language inside the "Choose your language" group and presses Start.
export async function chooseLanguageAndStart(page: Page, words: CustomerWords) {
  await page
    .getByRole('group', { name: LANGUAGE_CHOICE_GROUP_NAME })
    .getByRole('button', { name: words.languageChoice, exact: true })
    .click();
  await expect(page.locator('html')).toHaveAttribute('lang', words.language);
  await page.getByRole('button', { name: words.start, exact: true }).click();
}

// C2: types the monthly amount in rupees and presses Continue; the confirm line then shows.
export async function typeMonthlyBudget(page: Page, words: CustomerWords, rupees: string) {
  await expect(page.getByRole('heading', { level: 1, name: words.budgetTitle })).toBeVisible();
  await page.getByRole('textbox', { name: words.budgetAmountLabel }).fill(rupees);
  await page.getByRole('button', { name: words.budgetContinue, exact: true }).click();
  await expect(page.getByText(words.budgetConfirmQuestion)).toBeVisible();
}

// C2: confirms the amount the confirm line repeated; C3 opens.
export async function confirmMonthlyBudget(page: Page, words: CustomerWords) {
  await page.getByRole('button', { name: words.budgetConfirmYes }).click();
  await expect(
    page.getByRole('heading', { level: 1, name: words.comfortConsentTitle }),
  ).toBeVisible();
}

// C3: allows or skips the comfort check; C4 opens with its plans.
export async function answerComfortCheck(
  page: Page,
  words: CustomerWords,
  answer: 'allow' | 'skip',
) {
  const button =
    answer === 'allow'
      ? page.getByRole('button', { name: words.comfortAllow, exact: true })
      : page.getByRole('button', { name: new RegExp(`^${words.comfortSkip}`) });
  await button.click();
  await expect(page.getByRole('heading', { level: 1, name: words.plansTitle })).toBeVisible();
  await expect(planCards(page)).toHaveCount(3);
}

// C4: every plan card, in the order the server ranked them.
export function planCards(page: Page) {
  return page.getByRole('main').getByRole('article');
}

// C4: chooses the no-cost 6-month plan and continues to C6.
export async function chooseNoCostPlan(page: Page, words: CustomerWords) {
  await page.getByRole('radio', { name: words.noCostPlanRadio }).check();
  await page.getByRole('button', { name: words.plansContinue, exact: true }).click();
  await expect(
    page.getByRole('heading', { level: 1, name: words.alternativesTitle }),
  ).toBeVisible();
}

// C6: keeps the plan (Continue) and lands on C7 with its explanation text loaded.
export async function keepPlanAndReadExplanation(page: Page, words: CustomerWords) {
  await page.getByRole('button', { name: words.alternativesContinue, exact: true }).click();
  await expect(page.getByRole('heading', { level: 1, name: words.explanationTitle })).toBeVisible();
  // The server's text carries the language it was written in.
  await expect(explanationText(page, words)).toBeVisible();
}

// C7: the explanation paragraph in the customer's language.
export function explanationText(page: Page, words: CustomerWords) {
  return page.getByRole('main').locator(`p[lang="${words.language}"]`);
}

// C7 to C9: continues to confirm and asks for the OTP; the six boxes for the phone ending 42 show.
export async function continueToConsentAndSendOtp(page: Page, words: CustomerWords) {
  await page.getByRole('button', { name: words.explanationContinue }).click();
  await expect(page.getByRole('heading', { level: 1, name: words.consentTitle })).toBeVisible();
  await page.getByRole('button', { name: words.sendOtp }).click();
  await expect(page.getByRole('group', { name: words.otpGroupForPhoneEnding42 })).toBeVisible();
}

// C9: types an OTP into the six boxes from the first one and presses Confirm.
export async function enterOtpAndConfirm(page: Page, words: CustomerWords, otp: string) {
  await page.getByRole('textbox', { name: words.firstOtpDigit }).click();
  await page.keyboard.type(otp);
  await page.getByRole('button', { name: words.confirm, exact: true }).click();
}

// C10: the handoff screen with the consent reference (EMI-...).
export async function expectHandoffWithReference(page: Page, words: CustomerWords) {
  await expect(
    page.getByRole('heading', { level: 1, name: words.receiptReadyTitle }),
  ).toBeVisible();
  await expect(page.getByRole('region', { name: words.planSummaryHeading })).toContainText(
    new RegExp(`${words.receiptReference}\\s*EMI-[A-Z0-9-]+`),
  );
}
