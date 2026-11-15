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

/** Layer 4: the English text written by the audited AI, the Tamil one by the template. */
const AI_WRITTEN_WEEKLY_MESSAGE: typeof TEST_WEEKLY_MESSAGE = {
  ...SENT_WEEKLY_MESSAGE,
  source: 'AI_AUDITED',
  messages: {
    en: { ...TEST_WEEKLY_MESSAGE.messages.en, source: 'AI_AUDITED' },
    ta: { ...TEST_WEEKLY_MESSAGE.messages.ta, source: 'TEMPLATE' },
  },
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

  it('notes AI-written text only for the language the AI wrote, with no Listen', async () => {
    const { container } = renderWeeklyMessage({
      'GET /api/v1/reports/weekly-message': () => jsonResponse(AI_WRITTEN_WEEKLY_MESSAGE),
    });

    const message = await screen.findByRole('article');
    expect(within(message).getByText('Written by AI from your shop’s numbers')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Listen/ })).toBeNull();
    await expectNoAccessibilityViolations(container);

    await userEvent.click(screen.getByRole('button', { name: 'தமிழ்' }));
    expect(screen.queryByText('உங்கள் கடையின் எண்களிலிருந்து AI எழுதியது')).toBeNull();
  });

  it('shows no AI note for template text', async () => {
    renderWeeklyMessage();

    await screen.findByRole('article');

    expect(screen.queryByText('Written by AI from your shop’s numbers')).toBeNull();
  });

  it('notes AI-written text on the M5 summary card too', async () => {
    const { container } = renderMerchantApp({
      path: '/report',
      routes: {
        'GET /api/v1/reports/funnel': () => jsonResponse(TEST_FUNNEL_REPORT),
        'GET /api/v1/reports/weekly-message': () => jsonResponse(AI_WRITTEN_WEEKLY_MESSAGE),
      },
    });

    const summary = await screen.findByRole('region', { name: 'This week in short' });
    expect(await within(summary).findByText('Written by AI from your shop’s numbers')).toBeTruthy();
    await expectNoAccessibilityViolations(container);
  });
});
