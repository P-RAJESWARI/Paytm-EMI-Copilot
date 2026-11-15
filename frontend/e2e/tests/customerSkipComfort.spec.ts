// Two calm customer paths on a phone: skipping the comfort check still lists every plan (without
// bands), and a QR link that was already used shows "Ask the shop for a new QR" (ADR 0022).
import { expect, test } from '@playwright/test';

import {
  answerComfortCheck,
  checkCustomerScreen,
  chooseLanguageAndStart,
  confirmMonthlyBudget,
  openCustomerQrLink,
  planCards,
  typeMonthlyBudget,
} from '../support/customerScreens';
import { startSaleThroughApi } from '../support/customerSales';
import { ENGLISH_CUSTOMER_WORDS as WORDS } from '../support/customerWords';
import { pairDeviceThroughApi } from '../support/mockCustomerSimulator';

/** Any comfort band word, which must not show once the check was skipped. */
const ANY_BAND_WORD = /Comfortable|Stretching|Risky/;

test('a customer who skips the comfort check still compares every plan, without bands', async ({
  page,
  request,
}) => {
  const { customerUrl } = await startSaleThroughApi(request, await pairDeviceThroughApi(request));
  await openCustomerQrLink(page, customerUrl);
  await chooseLanguageAndStart(page, WORDS);
  await typeMonthlyBudget(page, WORDS, '3000');
  await confirmMonthlyBudget(page, WORDS);

  await answerComfortCheck(page, WORDS, 'skip');

  const cards = planCards(page);
  await expect(cards.filter({ hasText: 'Each month₹3,667' })).toContainText('Extra in total₹0');
  await expect(cards.filter({ hasText: 'Each month₹3,850' })).toContainText('Extra in total₹1,100');
  await expect(cards.filter({ hasText: 'Each month₹2,050' })).toContainText('Extra in total₹2,600');
  await expect(page.getByRole('main')).not.toContainText(ANY_BAND_WORD);
  await expect(page.getByRole('button', { name: /^Comfort detail/ })).toHaveCount(0);
  await checkCustomerScreen(page, 'C4 plans without the comfort check', WORDS);
});

test('a QR link that was already used, or a reloaded page, asks calmly for a new QR', async ({
  page,
  context,
  request,
}) => {
  const { customerUrl } = await startSaleThroughApi(request, await pairDeviceThroughApi(request));
  await openCustomerQrLink(page, customerUrl);

  await test.step('the same link opened again on a second page', async () => {
    const secondPage = await context.newPage();
    await secondPage.goto(customerUrl);
    await expect(
      secondPage.getByRole('heading', { level: 1, name: WORDS.sessionUnavailableTitle }),
    ).toBeVisible();
    await expect(
      secondPage.getByText(
        'This QR has already been used or has timed out. The shop can show you a new one to scan.',
      ),
    ).toBeVisible();
    await expect(secondPage.getByRole('main')).not.toContainText(/error|invalid|denied|blocked/i);
    await checkCustomerScreen(secondPage, 'QR already used', WORDS);
    await secondPage.close();
  });

  await test.step('the first page reloaded: the token lived only in memory', async () => {
    await page.reload();
    await expect(
      page.getByRole('heading', { level: 1, name: WORDS.sessionUnavailableTitle }),
    ).toBeVisible();
  });
});
