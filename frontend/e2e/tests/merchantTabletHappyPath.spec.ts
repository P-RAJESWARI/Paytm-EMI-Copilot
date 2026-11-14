// The merchant happy path on the counter tablet (1024 x 768), in English: pair, read the seeded
// week's report, start a sale, see "Ready to pay" arrive live, take payment by Mock link, see Paid.
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

import { expectNoAccessibilityViolations } from '../support/accessibility';
import {
  expectNoCustomerPrivateWords,
  pairThisDevice,
  startSaleForProduct,
} from '../support/merchantScreens';
import {
  agreeToPlanAsTheCustomer,
  completePaymentAsTheCustomer,
  MOCK_NO_COST_SIX_MONTH_OFFER_ID,
  pairDeviceThroughApi,
  readLatestPaymentLinkOrderId,
} from '../support/mockCustomerSimulator';

// M2: the seeded "At the counter now" list shows today's three customers with their statuses.
async function expectSeededCounterList(page: Page) {
  const counterList = page.getByRole('region', { name: 'At the counter now' });
  await expect(counterList.getByRole('listitem').filter({ hasText: 'Code 4821' })).toContainText(
    'Choosing on their phone',
  );
  await expect(counterList.getByRole('listitem').filter({ hasText: 'Code 4817' })).toContainText(
    'Ready to pay',
  );
  await expect(counterList.getByRole('listitem').filter({ hasText: 'Code 4812' })).toContainText(
    /Paid at \d{1,2}:\d{2}/,
  );
}

// M5: "This week" shows the seeded design funnel and the biggest drop (DESIGN_SPEC section 4).
async function expectSeededWeekFunnel(page: Page) {
  await expect(page.getByRole('button', { name: 'This week' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  const funnel = page.getByRole('region', { name: 'Where customers drop off' });
  await expect(funnel.getByRole('listitem')).toHaveText([
    'Started120',
    'Told a budget96',
    'Saw the plans88',
    'Agreed to a plan51',
    'Paid44',
  ]);
  await expect(
    funnel.getByText('37 customers left after seeing the plans. That is the biggest drop.'),
  ).toBeVisible();
}

// M5 and M6: Missed sales opens in place with the 12 customers under ₹3,000 and the budget chart,
// and "Share with brand rep" puts a summary with those figures on the clipboard.
async function expectMissedSalesPanelAndShare(page: Page) {
  await page
    .getByRole('button', {
      name: /12 customers wanted under ₹3,000 a month with nothing extra\. No plan fit\./,
    })
    .click();
  const missedSalesPanel = page.getByRole('region', { name: 'Missed sales detail' });
  await expect(
    missedSalesPanel.getByText('Example phone, 128 GB: the lowest no-cost plan is ₹3,667 a month.'),
  ).toBeVisible();
  await expect(
    missedSalesPanel.getByRole('table', { name: 'Monthly budgets customers entered (96)' }),
  ).toBeAttached();
  await missedSalesPanel.getByRole('button', { name: 'Share with brand rep' }).click();
  await expect(
    missedSalesPanel.getByText('Copied. Paste it in a message to your brand rep.'),
  ).toBeVisible();
  const sharedText = await page.evaluate(() => navigator.clipboard.readText());
  expect(sharedText).toContain('12 customers');
  expect(sharedText).toContain('₹3,000');
}

// M5 and M7: Money due from brands opens in place with ₹1,84,000 in three dated batches.
async function expectMoneyDuePanel(page: Page) {
  await page.getByRole('button', { name: /Money due from brands.*₹1,84,000/ }).click();
  const moneyDuePanel = page.getByRole('region', { name: 'Money due from brands detail' });
  await expect(moneyDuePanel.getByRole('listitem')).toHaveText([
    /Batch 1.*Expected 13 Jan 2027.*₹72,000/,
    /Batch 2.*Expected 28 Jan 2027.*₹64,000/,
    /Batch 3.*Expected 12 Feb 2027.*₹48,000/,
  ]);
}

// M3: the new sale's QR code shows while the customer is still choosing.
async function expectQrCodeWhileChoosing(page: Page) {
  await expect(
    page.getByRole('heading', { level: 1, name: 'Show this QR to the customer' }),
  ).toBeVisible();
  await expect(page.getByRole('img', { name: /^Session QR code \d{4}$/ })).toBeVisible();
  await expect(
    page.getByRole('region', { name: 'The customer is choosing a plan on their phone' }),
  ).toContainText('Choosing');
  await expectNoCustomerPrivateWords(page, 'M3 show QR while choosing');
  await expectNoAccessibilityViolations(page, 'M3 show QR while choosing');
}

// M3: once the customer agrees (through the simulator), the open page turns to "Ready to pay" with
// the plan's figures, without a reload: the update arrives on the live sale-status stream.
async function expectReadyToPayArrivesLive(
  page: Page,
  request: APIRequestContext,
  simulatorAccessToken: string,
  saleId: string,
) {
  await agreeToPlanAsTheCustomer(
    request,
    simulatorAccessToken,
    saleId,
    MOCK_NO_COST_SIX_MONTH_OFFER_ID,
  );
  const statusCard = page.getByRole('region', { name: 'The customer agreed to a plan' });
  await expect(statusCard).toContainText('Ready to pay');
  await expect(statusCard).toContainText('No-cost EMI, 6 months');
  await expect(statusCard).toContainText('Each month₹3,667');
  await expect(statusCard).toContainText('Extra in total₹0');
  await expect(statusCard).toContainText('Total₹22,000');
  await expectNoCustomerPrivateWords(page, 'M3 ready to pay');
  await expectNoAccessibilityViolations(page, 'M3 ready to pay');
}

// M4: "Take payment" opens the EDC steps and the payment status, still waiting.
async function expectTakePaymentWaiting(page: Page, saleId: string) {
  await page
    .getByRole('region', { name: 'The customer agreed to a plan' })
    .getByRole('link', { name: 'Take payment' })
    .click();
  await expect(page).toHaveURL(new RegExp(`/sale/${saleId}/handoff$`));
  await expect(page.getByRole('region', { name: 'Waiting for payment' })).toBeVisible();
  await expect(page.getByText('Choose Brand EMI.')).toBeVisible();
  await expectNoCustomerPrivateWords(page, 'M4 take payment');
  await expectNoAccessibilityViolations(page, 'M4 take payment');
}

// M4: the payment link QR appears; when the customer pays the Mock link, Paid arrives live.
async function expectPaidAfterMockLinkIsPaid(
  page: Page,
  request: APIRequestContext,
  simulatorAccessToken: string,
  saleId: string,
) {
  await page.getByRole('button', { name: 'Send payment link' }).click();
  const paymentLink = page.getByRole('region', { name: 'Payment link' });
  await expect(paymentLink.getByRole('img', { name: 'Payment link QR code' })).toBeVisible();
  await expectNoAccessibilityViolations(page, 'M4 with the payment link');
  const orderId = await readLatestPaymentLinkOrderId(request, simulatorAccessToken, saleId);
  await completePaymentAsTheCustomer(request, simulatorAccessToken, orderId);
  await expect(page.getByRole('region', { name: 'Paid' })).toContainText(
    /Confirmed by the server at \d{1,2}:\d{2}/,
  );
  await expectNoCustomerPrivateWords(page, 'M4 paid');
  await expectNoAccessibilityViolations(page, 'M4 paid');
}

test('a paired counter tablet sells on EMI from the QR code to a payment the server confirmed', async ({
  page,
  request,
}) => {
  const saleStatusStream = page.waitForResponse((response) =>
    response.url().endsWith('/api/v1/sales/events'),
  );
  await page.goto('/pair');
  await expect(page.getByRole('heading', { level: 1, name: 'Pair this device' })).toBeVisible();
  await expectNoAccessibilityViolations(page, 'M1 pairing');
  await pairThisDevice(page);

  await test.step('M2 lists the seeded customers at the counter', async () => {
    await expectSeededCounterList(page);
    await expectNoCustomerPrivateWords(page, 'M2 new EMI sale');
    await expectNoAccessibilityViolations(page, 'M2 new EMI sale');
  });

  // The report is checked before this test starts its own sale, which would add to the week.
  await test.step('M5 shows the seeded week before this sale is added', async () => {
    await page.getByRole('link', { name: 'Sales report' }).click();
    await expectSeededWeekFunnel(page);
    await expectMissedSalesPanelAndShare(page);
    await expectNoAccessibilityViolations(page, 'M5 sales report with Missed sales open');
    await expectMoneyDuePanel(page);
    await expectNoAccessibilityViolations(page, 'M5 sales report with Money due open');
  });

  await page.getByRole('link', { name: 'New EMI sale' }).click();
  const saleId = await startSaleForProduct(page, 'Example phone, 128 GB');
  await test.step('M3 shows the QR code while the customer chooses', async () => {
    await expectQrCodeWhileChoosing(page);
  });

  const simulatorAccessToken = await pairDeviceThroughApi(request);
  await test.step('M3 turns to "Ready to pay" live, without a reload, once the customer agrees', async () => {
    const stream = await saleStatusStream;
    expect(stream.status()).toBe(200);
    expect(stream.headers()['content-type']).toContain('text/event-stream');
    await expectReadyToPayArrivesLive(page, request, simulatorAccessToken, saleId);
  });

  await test.step('M4 shows the EDC steps and waits for the payment', async () => {
    await expectTakePaymentWaiting(page, saleId);
  });

  await test.step('M4 shows Paid once the Mock payment link is paid', async () => {
    await expectPaidAfterMockLinkIsPaid(page, request, simulatorAccessToken, saleId);
  });
});
