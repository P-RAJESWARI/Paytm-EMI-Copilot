// The merchant phone width (360 x 800): M3 fits without sideways scrolling and shows the plan totals
// once the customer agrees, and M8 reads the weekly message in Tamil.
import { expect, test } from '@playwright/test';

import { expectNoAccessibilityViolations } from '../support/accessibility';
import {
  expectEveryStringTranslated,
  expectNoHorizontalScroll,
  pairThisDevice,
  startSaleForProduct,
} from '../support/merchantScreens';
import {
  agreeToPlanAsTheCustomer,
  MOCK_NO_COST_SIX_MONTH_OFFER_ID,
  pairDeviceThroughApi,
} from '../support/mockCustomerSimulator';

const PHONE_VIEWPORT_WIDTH = 360;

test('M3 on a phone shows the whole QR code without sideways scrolling, then the agreed plan totals', async ({
  page,
  request,
}) => {
  await pairThisDevice(page);
  const saleId = await startSaleForProduct(page, 'Example phone, 128 GB');

  await test.step('the QR code fits the phone screen', async () => {
    const qrCode = page.getByRole('img', { name: /^Session QR code \d{4}$/ });
    await expect(qrCode).toBeVisible();
    const qrCodeBox = await qrCode.boundingBox();
    expect(qrCodeBox).not.toBeNull();
    expect((qrCodeBox?.x ?? 0) + (qrCodeBox?.width ?? 0)).toBeLessThanOrEqual(PHONE_VIEWPORT_WIDTH);
    await expectNoHorizontalScroll(page);
    await expectNoAccessibilityViolations(page, 'M3 on a phone while choosing');
  });

  await test.step('the agreed plan totals appear live', async () => {
    const simulatorAccessToken = await pairDeviceThroughApi(request);
    await agreeToPlanAsTheCustomer(
      request,
      simulatorAccessToken,
      saleId,
      MOCK_NO_COST_SIX_MONTH_OFFER_ID,
    );
    const statusCard = page.getByRole('region', { name: 'The customer agreed to a plan' });
    await expect(statusCard).toContainText('Ready to pay');
    await expect(statusCard).toContainText('Each month₹3,667');
    await expect(statusCard).toContainText('Extra in total₹0');
    await expect(statusCard).toContainText('Total₹22,000');
    await expectNoHorizontalScroll(page);
    await expectNoAccessibilityViolations(page, 'M3 on a phone, ready to pay');
  });
});

test('M8 on a phone reads the weekly message in Tamil', async ({ page }) => {
  await pairThisDevice(page);
  await page
    .getByRole('navigation', { name: 'Main' })
    .getByRole('button', { name: 'தமிழ்' })
    .click();
  await page.getByRole('link', { name: 'விற்பனை அறிக்கை' }).click();
  await page.getByRole('link', { name: 'போனில் வருவது போல் பார்' }).click();

  await expect(page).toHaveURL(/\/report\/weekly-message$/);
  await expect(page.getByText('வாராந்திரச் செய்தி')).toBeVisible();
  await expect(page.getByRole('article')).toBeVisible();
  await expect(page.locator('[lang="ta"]').first()).toBeVisible();
  await expect(page.getByRole('link', { name: 'விற்பனை அறிக்கையைத் திற' })).toBeVisible();
  await expectEveryStringTranslated(page, 'M8 in Tamil');
  await expectNoHorizontalScroll(page);
  await expectNoAccessibilityViolations(page, 'M8 in Tamil');
});
