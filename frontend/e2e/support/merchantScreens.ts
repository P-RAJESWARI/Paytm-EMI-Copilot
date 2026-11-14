// Steps and checks shared by the merchant end-to-end tests. Navigation goes through the app's own
// links only: the bearer token lives in page memory, so a page reload would unpair the device.
import { expect, test, type Page } from '@playwright/test';

import { DEMO_SHOP_ID, readDemoShopPin } from './endToEndSettings';

/**
 * Words that would reveal a customer's finances, comfort check or progress (rule 6), in English
 * and Tamil. Same list as the component privacy test (merchantScreensPrivacy.test.tsx).
 */
const CUSTOMER_PRIVATE_WORDS =
  /income|EMIs you already pay|existing EMI|comfort|ratio|basis point|Comfortable|Stretching|Risky|budget|approved|declined|rejected|eligible|scanned|step|வருமான|வசதியானது|சிரமம்|அதிக சுமை|பட்ஜெட்/i;

/** A translation key shown instead of its text, such as "report.funnel.title", or a {{gap}}. */
const UNTRANSLATED_TEXT =
  /\b(?:common|language|saleStatus|brandPanel|shell|pairing|problems|plan|counterSale|counterList|showQr|handoff|report|weeklyMessage)\.[A-Za-z]|\{\{/;

// M1: types the shop ID and the e2e PIN, presses "Pair device" and lands on New EMI sale.
export async function pairThisDevice(page: Page) {
  await test.step('pair this device with the demo shop', async () => {
    await page.goto('/pair');
    await expect(page.getByRole('heading', { level: 1, name: 'Pair this device' })).toBeVisible();
    await page.getByLabel('Shop ID').fill(DEMO_SHOP_ID);
    await page.getByRole('textbox', { name: 'PIN digit 1 of 6' }).click();
    await page.keyboard.type(readDemoShopPin());
    await page.getByRole('button', { name: 'Pair device' }).click();
    await expect(page).toHaveURL(/\/sale$/);
  });
}

// M2: picks the product and presses "Show QR to customer"; gives the new sale's id from the M3 URL.
export async function startSaleForProduct(page: Page, productName: string): Promise<string> {
  return test.step(`start an EMI sale for ${productName}`, async () => {
    // The radio is visually hidden inside its row, so press the row's product name as a person would.
    const productList = page.getByRole('group', { name: 'Products' });
    await productList.getByText(productName, { exact: true }).click();
    await expect(
      productList.getByRole('radio', { name: new RegExp(escapeForPattern(productName)) }),
    ).toBeChecked();
    await page.getByRole('button', { name: 'Show QR to customer' }).click();
    await expect(page).toHaveURL(/\/sale\/[^/]+\/qr$/);
    const saleId = /\/sale\/([^/]+)\/qr$/.exec(new URL(page.url()).pathname)?.[1];
    if (saleId === undefined) throw new Error(`No sale id in ${page.url()}`);
    return decodeURIComponent(saleId);
  });
}

// Gives all page text except the one note that reassures the merchant about customer privacy.
async function readPageTextWithoutPrivacyNote(page: Page): Promise<string> {
  return page.evaluate(() => {
    const pageCopy = document.body.cloneNode(true) as HTMLElement;
    pageCopy.querySelectorAll('[data-privacy-note]').forEach((privacyNote) => {
      privacyNote.remove();
    });
    return pageCopy.textContent;
  });
}

// Fails when the page shows any customer finance, comfort-check or progress word (rule 6).
export async function expectNoCustomerPrivateWords(page: Page, screenName: string) {
  await test.step(`${screenName} shows no customer finances or progress`, async () => {
    expect(await readPageTextWithoutPrivacyNote(page)).not.toMatch(CUSTOMER_PRIVATE_WORDS);
  });
}

// Fails when the page shows a raw translation key or an unfilled {{placeholder}}.
export async function expectEveryStringTranslated(page: Page, screenName: string) {
  await test.step(`${screenName} shows no raw translation keys`, async () => {
    expect(await page.locator('body').innerText()).not.toMatch(UNTRANSLATED_TEXT);
  });
}

// Fails when the page is wider than the viewport, so the merchant would have to scroll sideways.
export async function expectNoHorizontalScroll(page: Page) {
  const widths = await page.evaluate(() => ({
    contentWidth: document.documentElement.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
  }));
  expect(widths.contentWidth).toBeLessThanOrEqual(widths.viewportWidth);
}

// Turns a product name into a pattern that matches it literally (it contains a comma and spaces).
function escapeForPattern(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
