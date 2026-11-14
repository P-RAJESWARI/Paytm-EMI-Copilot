import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { jsonResponse, problemResponse, type FakeRoutes } from '../testing/fakeMerchantBackend';
import { renderMerchantApp } from '../testing/renderMerchantApp';
import { TEST_FUNNEL_REPORT, TEST_WEEKLY_MESSAGE } from '../testing/salesReportTestData';

const SENT_WEEKLY_MESSAGE = {
  ...TEST_WEEKLY_MESSAGE,
  isSent: true,
  sentAt: '2026-11-16T03:30:00Z',
};

// Renders M8 with a sent message unless a test replaces the route.
function renderWeeklyMessage(routes: FakeRoutes = {}) {
  return renderMerchantApp({
    path: '/report/weekly-message',
    routes: {
      'GET /api/v1/reports/weekly-message': () => jsonResponse(SENT_WEEKLY_MESSAGE),
      ...routes,
    },
  });
}

afterEach(() => {
  window.localStorage.clear();
});

describe('M8 weekly message on the phone', () => {
  it('shows the message chat-style with when it was sent, outside the tablet shell', async () => {
    renderWeeklyMessage();

    expect(screen.getByRole('status', { name: 'Loading this week’s summary…' })).toBeTruthy();
    const message = await screen.findByRole('article');
    expect(
      within(message).getByRole('heading', { level: 2, name: 'Your EMI sales, 9 to 15 November' }),
    ).toBeTruthy();
    expect(
      within(message).getByText(
        '12 customers wanted under ₹3,000 a month with nothing extra, and no plan fit.',
      ),
    ).toBeTruthy();
    expect(within(message).getByText('9:00 am')).toBeTruthy();
    expect(screen.getByText('Monday, 16 November')).toBeTruthy();
    expect(screen.getByText('Weekly message')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'Open sales report' }).getAttribute('href')).toBe(
      '/report',
    );
    expect(screen.queryByRole('navigation', { name: 'Main' })).toBeNull();
    expect(screen.queryByRole('button', { name: /Listen/ })).toBeNull();
  });

  it('starts in the shop language and switches with its own toggle', async () => {
    window.localStorage.setItem('emiCopilot.language', 'ta');
    renderWeeklyMessage();

    expect(
      await screen.findByRole('heading', {
        level: 2,
        name: 'உங்கள் EMI விற்பனை, 9 முதல் 15 நவம்பர்',
      }),
    ).toBeTruthy();
    expect(screen.getByText('வாராந்திரச் செய்தி')).toBeTruthy();

    await userEvent.click(screen.getByRole('button', { name: 'EN' }));

    expect(
      screen.getByRole('heading', { level: 2, name: 'Your EMI sales, 9 to 15 November' }),
    ).toBeTruthy();
    expect(window.localStorage.getItem('emiCopilot.language')).toBe('ta');
  });

  it('says when the message was not sent yet', async () => {
    renderWeeklyMessage({
      'GET /api/v1/reports/weekly-message': () => jsonResponse(TEST_WEEKLY_MESSAGE),
    });

    expect(await screen.findByText('Not sent to your phone yet')).toBeTruthy();
  });

  it('shows a calm error with retry', async () => {
    let shouldFail = true;
    renderWeeklyMessage({
      'GET /api/v1/reports/weekly-message': () =>
        shouldFail
          ? problemResponse(500, 'INTERNAL_SERVER_ERROR')
          : jsonResponse(SENT_WEEKLY_MESSAGE),
    });

    expect(await screen.findByText('Something did not load. Please try again.')).toBeTruthy();
    shouldFail = false;
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('article')).toBeTruthy();
  });

  it('opens from the M5 summary card link', async () => {
    const { router } = renderMerchantApp({
      path: '/report',
      routes: {
        'GET /api/v1/reports/funnel': () => jsonResponse(TEST_FUNNEL_REPORT),
        'GET /api/v1/reports/weekly-message': () => jsonResponse(SENT_WEEKLY_MESSAGE),
      },
    });

    await userEvent.click(await screen.findByRole('link', { name: 'See it as on your phone' }));

    expect(await screen.findByRole('article')).toBeTruthy();
    expect(router.state.location.pathname).toBe('/report/weekly-message');
  });

  it('has no accessibility violations', async () => {
    const { container } = renderWeeklyMessage();
    await screen.findByRole('article');

    await expectNoAccessibilityViolations(container);
  });
});
