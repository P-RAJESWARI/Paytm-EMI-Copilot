// The Tamil pass on the counter tablet: the sidebar language switch turns M2 and M5 into Tamil with
// no raw translation keys, and both stay free of accessibility violations. Reads only; starts no sale.
import { expect, test } from '@playwright/test';

import { expectNoAccessibilityViolations } from '../support/accessibility';
import { expectEveryStringTranslated, pairThisDevice } from '../support/merchantScreens';

test('the shop language switch shows New EMI sale and the sales report in Tamil', async ({
  page,
}) => {
  await pairThisDevice(page);
  const navigation = page.getByRole('navigation', { name: 'Main' });
  await navigation.getByRole('button', { name: 'தமிழ்' }).click();

  await test.step('M2 reads in Tamil', async () => {
    await expect(page.getByRole('navigation', { name: 'முதன்மை' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'புதிய EMI விற்பனை' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'விற்பனை அறிக்கை' })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: 'இப்போது கவுண்டரில்' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'வாடிக்கையாளருக்கு QR காட்டு' })).toBeAttached();
    await expectEveryStringTranslated(page, 'M2 in Tamil');
    await expectNoAccessibilityViolations(page, 'M2 in Tamil');
  });

  await test.step('M5 reads in Tamil', async () => {
    await page.getByRole('link', { name: 'விற்பனை அறிக்கை' }).click();
    const funnel = page.getByRole('region', { name: 'வாடிக்கையாளர்கள் எங்கே விலகுகிறார்கள்' });
    await expect(funnel.getByText('தொடங்கினர்')).toBeVisible();
    await expect(funnel.getByText('பணம் செலுத்தினர்')).toBeVisible();
    await expect(page.getByRole('button', { name: 'இந்த வாரம்' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await expectEveryStringTranslated(page, 'M5 in Tamil');
    await expectNoAccessibilityViolations(page, 'M5 in Tamil');
  });
});
