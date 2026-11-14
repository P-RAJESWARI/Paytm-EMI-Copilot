import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { jsonResponse, problemResponse, type FakeRoutes } from '../testing/fakeMerchantBackend';
import { renderMerchantApp } from '../testing/renderMerchantApp';
import {
  buildUniformFunnelReport,
  TEST_FUNNEL_REPORT,
  TEST_MISSED_SALES_REPORT,
  TEST_MONEY_DUE,
  TEST_SUGGESTED_ACTIONS,
  TEST_WEEKLY_MESSAGE,
} from '../testing/salesReportTestData';
import { stubClipboard } from '../testing/stubClipboard';

/** The missed-sales answer when 1 to 4 were missed: no count and nothing derived from it. */
const SUPPRESSED_MISSED_SALES_REPORT = {
  ...TEST_MISSED_SALES_REPORT,
  missedCustomerCount: null,
  isSuppressed: true,
  budgetCeilingInPaise: null,
  productInsight: null,
  budgetTotalCustomerCount: null,
  areBudgetBucketsHidden: true,
  budgetBuckets: [],
};

const SHARE_TEXT =
  'Ravi Electronics, This week: 12 customers wanted Example phone, 128 GB under ₹3,000 a month with nothing extra. The lowest no-cost plan is ₹3,667 a month. Could you offer a 9 or 12-month no-cost plan on this model?';

// Renders M5 with the design week unless a test replaces a route.
function renderSalesReport(routes: FakeRoutes = {}) {
  return renderMerchantApp({
    path: '/report',
    routes: {
      'GET /api/v1/reports/funnel': () => jsonResponse(TEST_FUNNEL_REPORT),
      'GET /api/v1/reports/missed-sales': () => jsonResponse(TEST_MISSED_SALES_REPORT),
      'GET /api/v1/reports/suggested-actions': () => jsonResponse(TEST_SUGGESTED_ACTIONS),
      'GET /api/v1/reports/money-due': () => jsonResponse(TEST_MONEY_DUE),
      'GET /api/v1/reports/weekly-message': () => jsonResponse(TEST_WEEKLY_MESSAGE),
      ...routes,
    },
  });
}

// Waits for the whole report, including both expandable cards.
async function waitForLoadedReport() {
  await screen.findByRole('button', { name: /Missed sales/ });
  await screen.findByRole('button', { name: /Money due from brands/ });
}

afterEach(() => {
  window.localStorage.clear();
});

describe('M5 sales report', () => {
  it('shows this week by default: summary, funnel, the two cards and the suggestions', async () => {
    renderSalesReport();

    expect(screen.getByRole('status', { name: 'Loading the sales report…' })).toBeTruthy();
    await waitForLoadedReport();
    expect(screen.getByRole('button', { name: 'This week' }).getAttribute('aria-pressed')).toBe(
      'true',
    );
    const funnel = screen.getByRole('region', { name: 'Where customers drop off' });
    expect(
      within(funnel)
        .getAllByRole('listitem')
        .map((row) => row.textContent),
    ).toEqual(['Started120', 'Told a budget96', 'Saw the plans88', 'Agreed to a plan51', 'Paid44']);
    expect(
      within(funnel).getByText(
        '37 customers left after seeing the plans. That is the biggest drop.',
      ),
    ).toBeTruthy();
    expect(
      screen.getByRole('button', {
        name: /12 customers wanted under ₹3,000 a month with nothing extra. No plan fit./,
      }),
    ).toBeTruthy();
    expect(
      screen.getByRole('button', { name: /₹1,84,000.*Next payment expected 13 Jan\./ }),
    ).toBeTruthy();
    const actions = screen.getByRole('region', { name: 'What you can do to sell more' });
    expect(
      within(actions).getByText(
        'Ask the brand for a longer no-cost plan on the Example phone, 128 GB',
      ),
    ).toBeTruthy();
    expect(
      within(actions).getByText(
        '9 or 12 months with nothing extra would be ₹2,444 or ₹1,833 a month. 12 customers wanted under ₹3,000 a month.',
      ),
    ).toBeTruthy();
    expect(
      within(actions).getByText('At ₹18,000 it is ₹3,000 a month for 6 months with nothing extra.'),
    ).toBeTruthy();
    const summary = screen.getByRole('region', { name: 'This week in short' });
    expect(within(summary).getByText('Your EMI sales, 9 to 15 November')).toBeTruthy();
    expect(
      within(summary).getByText(
        '44 of 120 customers bought on EMI. The biggest drop was after seeing the plans.',
      ),
    ).toBeTruthy();
    expect(within(summary).queryByRole('button', { name: /Listen/ })).toBeNull();
  });

  it('opens Missed sales in place below the grid, one card at a time', async () => {
    renderSalesReport();
    await waitForLoadedReport();
    const missedSalesButton = screen.getByRole('button', { name: /Missed sales/ });

    await userEvent.click(missedSalesButton);

    expect(missedSalesButton.getAttribute('aria-expanded')).toBe('true');
    const panel = screen.getByRole('region', { name: 'Missed sales detail' });
    expect(
      within(panel).getByText('Example phone, 128 GB: the lowest no-cost plan is ₹3,667 a month.'),
    ).toBeTruthy();
    expect(
      within(panel).getByText(
        'The plan under ₹3,000 a month with the least extra adds ₹2,600 extra in total.',
      ),
    ).toBeTruthy();
    expect(
      within(panel).getByText('Ask the brand for a 9 or 12-month no-cost plan on this model.'),
    ).toBeTruthy();
    const budgetTable = within(panel).getByRole('table', {
      name: 'Monthly budgets customers entered (96)',
    });
    expect(
      within(budgetTable)
        .getAllByRole('row')
        .slice(1)
        .map((row) => row.textContent),
    ).toEqual([
      'Under ₹2,5005Demo cardless lender (Mock) ₹2,050',
      '₹2,500 to ₹3,0007',
      '₹3,000 to ₹3,50014',
      "₹3,500 to ₹4,00021No-cost ₹3,667, Your card's bank ₹3,850",
      '₹4,000 and above49',
    ]);

    await userEvent.click(screen.getByRole('button', { name: /Money due from brands/ }));

    expect(missedSalesButton.getAttribute('aria-expanded')).toBe('false');
    expect(screen.queryByRole('region', { name: 'Missed sales detail' })).toBeNull();
    const moneyDuePanel = screen.getByRole('region', { name: 'Money due from brands detail' });
    expect(
      within(moneyDuePanel)
        .getAllByRole('listitem')
        .map((row) => row.textContent),
    ).toEqual([
      'Batch 1, 18 salesExpected 13 Jan 2027Claim filed₹72,000',
      'Batch 2, 16 salesExpected 28 Jan 2027Waiting for brand₹64,000',
      'Batch 3, 10 salesExpected 12 Feb 2027Not yet due₹48,000',
    ]);
    expect(
      within(moneyDuePanel).getByText('Dates are estimates from the brands’ offer terms.'),
    ).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: /Money due from brands/ }));
    expect(screen.queryByRole('region', { name: 'Money due from brands detail' })).toBeNull();
  });

  it('copies the brand-rep summary, built from the report figures, and confirms calmly', async () => {
    const writeText = vi.fn(() => Promise.resolve());
    stubClipboard({ writeText });
    renderSalesReport();
    await waitForLoadedReport();
    await userEvent.click(screen.getByRole('button', { name: /Missed sales/ }));

    await userEvent.click(screen.getByRole('button', { name: 'Share with brand rep' }));

    expect(writeText).toHaveBeenCalledWith(SHARE_TEXT);
    expect(
      await screen.findByText('Copied. Paste it in a message to your brand rep.'),
    ).toBeTruthy();
  });

  it('shows the brand-rep text to copy by hand when this device cannot copy', async () => {
    stubClipboard(undefined);
    renderSalesReport();
    await waitForLoadedReport();
    await userEvent.click(screen.getByRole('button', { name: /Missed sales/ }));

    await userEvent.click(screen.getByRole('button', { name: 'Share with brand rep' }));

    const fallbackText = await screen.findByLabelText<HTMLTextAreaElement>(
      'Copying is not available on this device. Select this text and copy it.',
    );
    expect(fallbackText.value).toBe(SHARE_TEXT);
  });

  it('switches the period and shows the calm empty state when no EMI sale started', async () => {
    const { fakeBackend } = renderSalesReport({
      'GET /api/v1/reports/funnel': ({ searchParameters }) =>
        jsonResponse(
          searchParameters.get('range') === 'TODAY'
            ? buildUniformFunnelReport('TODAY', 0)
            : TEST_FUNNEL_REPORT,
        ),
    });
    await waitForLoadedReport();

    await userEvent.click(screen.getByRole('button', { name: 'Today' }));

    expect(
      await screen.findByRole('heading', { level: 2, name: 'No EMI sales today yet' }),
    ).toBeTruthy();
    expect(
      screen.getByText(
        'When a customer asks about EMI, start a new EMI sale. Your report fills in as customers finish choosing.',
      ),
    ).toBeTruthy();
    expect(
      within(screen.getByRole('main'))
        .getByRole('link', { name: 'New EMI sale' })
        .getAttribute('href'),
    ).toBe('/sale');
    expect(screen.queryByRole('region', { name: 'Where customers drop off' })).toBeNull();
    expect(
      fakeBackend.recordedRequests.some(
        (request) => request.path === '/api/v1/reports/funnel?range=TODAY',
      ),
    ).toBe(true);
  });

  it('shows "fewer than 5" for hidden counts, names a hidden drop without a number and hides the chart', async () => {
    const { container } = renderSalesReport({
      'GET /api/v1/reports/funnel': () =>
        jsonResponse({
          ...TEST_FUNNEL_REPORT,
          stages: TEST_FUNNEL_REPORT.stages.map((stage) =>
            stage.stage === 'PAID' ? { ...stage, customerCount: null, isSuppressed: true } : stage,
          ),
          biggestDrop: { afterStage: 'AGREED', customerCount: null, isSuppressed: true },
        }),
      'GET /api/v1/reports/missed-sales': () => jsonResponse(SUPPRESSED_MISSED_SALES_REPORT),
      'GET /api/v1/reports/suggested-actions': () => jsonResponse({ actions: [] }),
    });
    await waitForLoadedReport();

    const funnel = screen.getByRole('region', { name: 'Where customers drop off' });
    expect(within(funnel).getAllByRole('listitem').at(-1)?.textContent).toBe('Paidfewer than 5');
    expect(within(funnel).getByText('The biggest drop was after agreeing to a plan.')).toBeTruthy();
    await userEvent.click(
      screen.getByRole('button', {
        name: /Fewer than 5 customers wanted a lower monthly amount with nothing extra\. No plan fit\./,
      }),
    );
    const panel = screen.getByRole('region', { name: 'Missed sales detail' });
    expect(
      within(panel).getByText(
        'Fewer than 5 customers missed out in this period, so the detail stays hidden to keep their answers private.',
      ),
    ).toBeTruthy();
    expect(
      within(panel).getByText(
        'Fewer than 5 customers told a budget in this period, so this chart stays hidden to keep their answers private.',
      ),
    ).toBeTruthy();
    expect(within(panel).queryByRole('button', { name: 'Share with brand rep' })).toBeNull();
    expect(panel.textContent).not.toMatch(/₹/);
    await expectNoAccessibilityViolations(container);
  });

  it('hides a drop beside a suppressed stage and the zeros after it, without a false "fewer than 5"', async () => {
    renderSalesReport({
      'GET /api/v1/reports/funnel': () =>
        jsonResponse({
          ...TEST_FUNNEL_REPORT,
          stages: TEST_FUNNEL_REPORT.stages.map((stage) =>
            stage.stage === 'STARTED'
              ? { ...stage, customerCount: 20 }
              : { ...stage, customerCount: null, isSuppressed: true },
          ),
          biggestDrop: { afterStage: 'STARTED', customerCount: null, isSuppressed: true },
        }),
    });
    await waitForLoadedReport();

    const funnel = screen.getByRole('region', { name: 'Where customers drop off' });
    expect(
      within(funnel)
        .getAllByRole('listitem')
        .map((row) => row.textContent),
    ).toEqual([
      'Started20',
      'Told a budgetfewer than 5',
      'Saw the plansfewer than 5',
      'Agreed to a planfewer than 5',
      'Paidfewer than 5',
    ]);
    expect(within(funnel).getByText('The biggest drop was after starting.')).toBeTruthy();
    expect(funnel.textContent).not.toMatch(/left after/);
  });

  it('shows the budget chart without a ceiling legend or plans when the missed count is hidden', async () => {
    const { container } = renderSalesReport({
      'GET /api/v1/reports/missed-sales': () =>
        jsonResponse({
          ...SUPPRESSED_MISSED_SALES_REPORT,
          budgetTotalCustomerCount: 12,
          areBudgetBucketsHidden: false,
          budgetBuckets: TEST_MISSED_SALES_REPORT.budgetBuckets.slice(0, 2).map((bucket) => ({
            ...bucket,
            customerCount: 6,
            isUnderCeiling: false,
            plans: [],
          })),
        }),
      'GET /api/v1/reports/suggested-actions': () => jsonResponse({ actions: [] }),
    });
    await waitForLoadedReport();

    await userEvent.click(screen.getByRole('button', { name: /Missed sales/ }));

    const panel = screen.getByRole('region', { name: 'Missed sales detail' });
    const budgetTable = within(panel).getByRole('table', {
      name: 'Monthly budgets customers entered (12)',
    });
    expect(
      within(budgetTable)
        .getAllByRole('columnheader')
        .map((header) => header.textContent),
    ).toEqual(['Monthly budget', 'Customers']);
    expect(
      within(budgetTable)
        .getAllByRole('row')
        .slice(1)
        .map((row) => row.textContent),
    ).toEqual(['Under ₹2,5006', '₹2,500 to ₹3,0006']);
    expect(within(panel).queryByText(/and above$/)).toBeNull();
    expect(within(panel).queryByText(/^Under ₹3,000$/)).toBeNull();
    await expectNoAccessibilityViolations(container);
  });

  it('labels hidden budget buckets "Hidden", never "fewer than 5", in the chart, its table and Tamil', async () => {
    const { container } = renderSalesReport({
      'GET /api/v1/reports/missed-sales': () =>
        jsonResponse({
          ...TEST_MISSED_SALES_REPORT,
          // Complementary suppression: the second hidden bucket may hold 5 or more.
          budgetBuckets: TEST_MISSED_SALES_REPORT.budgetBuckets.map((bucket, bucketIndex) =>
            bucketIndex < 2 ? { ...bucket, customerCount: null, isSuppressed: true } : bucket,
          ),
        }),
    });
    await waitForLoadedReport();

    await userEvent.click(screen.getByRole('button', { name: /Missed sales/ }));

    const panel = screen.getByRole('region', { name: 'Missed sales detail' });
    const budgetTable = within(panel).getByRole('table', {
      name: 'Monthly budgets customers entered (96)',
    });
    expect(
      within(budgetTable)
        .getAllByRole('row')
        .slice(1)
        .map((row) => row.textContent),
    ).toEqual([
      'Under ₹2,500HiddenDemo cardless lender (Mock) ₹2,050',
      '₹2,500 to ₹3,000Hidden',
      '₹3,000 to ₹3,50014',
      "₹3,500 to ₹4,00021No-cost ₹3,667, Your card's bank ₹3,850",
      '₹4,000 and above49',
    ]);
    expect(within(panel).getAllByText('Hidden')).toHaveLength(4);
    expect(
      within(panel).getByText('Some ranges are hidden to keep customers’ answers private.'),
    ).toBeTruthy();
    expect(panel.textContent).not.toMatch(/fewer than 5/i);
    await expectNoAccessibilityViolations(container);

    await userEvent.click(
      within(screen.getByRole('navigation', { name: 'Main' })).getByRole('button', {
        name: 'தமிழ்',
      }),
    );

    const tamilPanel = screen.getByRole('region', { name: 'தவறிய விற்பனை விவரம்' });
    expect(within(tamilPanel).getAllByText('மறைக்கப்பட்டது')).toHaveLength(4);
    expect(tamilPanel.textContent).not.toMatch(/5-க்கும் குறைவான/);
  });

  it('gives the missed count without a ceiling when the API sends none', async () => {
    renderSalesReport({
      'GET /api/v1/reports/missed-sales': () =>
        jsonResponse({
          ...TEST_MISSED_SALES_REPORT,
          budgetCeilingInPaise: null,
          productInsight: null,
        }),
    });
    await waitForLoadedReport();

    await userEvent.click(
      screen.getByRole('button', {
        name: /12 customers wanted a lower monthly amount with nothing extra\. No plan fit\./,
      }),
    );

    expect(
      screen.getByText('No single product had enough missed sales in this period to name it.'),
    ).toBeTruthy();
  });

  it('says calmly when there are no missed sales, nothing due and nothing to suggest', async () => {
    renderSalesReport({
      'GET /api/v1/reports/missed-sales': () =>
        jsonResponse({
          ...TEST_MISSED_SALES_REPORT,
          missedCustomerCount: 0,
          budgetCeilingInPaise: null,
          productInsight: null,
        }),
      'GET /api/v1/reports/money-due': () =>
        jsonResponse({ totalDueInPaise: 0, nextExpectedDate: null, batches: [] }),
      'GET /api/v1/reports/suggested-actions': () => jsonResponse({ actions: [] }),
    });
    await waitForLoadedReport();

    await userEvent.click(screen.getByRole('button', { name: /No missed sales in this period\./ }));
    const panel = screen.getByRole('region', { name: 'Missed sales detail' });
    expect(within(panel).getByText('No missed sales in this period.')).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Share with brand rep' })).toBeNull();
    await userEvent.click(
      screen.getByRole('button', { name: /Nothing is due from brands right now\./ }),
    );
    expect(screen.getByText('No batches are waiting for payment.')).toBeTruthy();
    expect(await screen.findByText('Nothing to suggest for this period yet.')).toBeTruthy();
  });

  it('sends the weekly message to the phone and then says it was sent', async () => {
    const { fakeBackend } = renderSalesReport({
      'POST /api/v1/reports/weekly-message/send': () =>
        jsonResponse({ ...TEST_WEEKLY_MESSAGE, isSent: true, sentAt: '2026-11-16T03:30:00Z' }),
    });
    const summary = await screen.findByRole('region', { name: 'This week in short' });

    await userEvent.click(await within(summary).findByRole('button', { name: 'Send to my phone' }));

    expect(await within(summary).findByText('Sent to your phone')).toBeTruthy();
    expect(within(summary).queryByRole('button', { name: 'Send to my phone' })).toBeNull();
    expect(fakeBackend.recordedRequests.find((request) => request.method === 'POST')?.body).toEqual(
      { periodStartDate: '2026-11-09' },
    );
    expect(
      within(summary).getByRole('link', { name: 'See it as on your phone' }).getAttribute('href'),
    ).toBe('/report/weekly-message');
  });

  it('switches only the weekly message to Tamil with its own toggle', async () => {
    renderSalesReport();
    const summary = await screen.findByRole('region', { name: 'This week in short' });
    await within(summary).findByText('Your EMI sales, 9 to 15 November');

    await userEvent.click(within(summary).getByRole('button', { name: 'தமிழ்' }));

    const tamilSummary = screen.getByRole('region', { name: 'இந்த வாரச் சுருக்கம்' });
    expect(tamilSummary.getAttribute('lang')).toBe('ta');
    expect(within(tamilSummary).getByText('உங்கள் EMI விற்பனை, 9 முதல் 15 நவம்பர்')).toBeTruthy();
    expect(screen.getByRole('heading', { level: 1, name: 'Sales report' })).toBeTruthy();
  });

  it('explains calmly when the weekly message cannot be read or sent', async () => {
    renderSalesReport({
      'GET /api/v1/reports/weekly-message': () => problemResponse(500, 'INTERNAL_SERVER_ERROR'),
    });
    const summary = await screen.findByRole('region', { name: 'This week in short' });
    expect(
      await within(summary).findByText('Something did not load. Please try again.'),
    ).toBeTruthy();
  });

  it('explains calmly when sending fails', async () => {
    renderSalesReport({
      'POST /api/v1/reports/weekly-message/send': () =>
        problemResponse(502, 'PAYMENT_GATEWAY_ERROR'),
    });
    const summary = await screen.findByRole('region', { name: 'This week in short' });

    await userEvent.click(await within(summary).findByRole('button', { name: 'Send to my phone' }));

    expect(await within(summary).findByRole('alert')).toBeTruthy();
  });

  it('shows calm errors with retry for each part that did not load', async () => {
    let shouldFail = true;
    const failingRoute = () =>
      shouldFail ? problemResponse(503, 'SERVICE_UNAVAILABLE') : jsonResponse(TEST_MONEY_DUE);
    renderSalesReport({
      'GET /api/v1/reports/missed-sales': () => problemResponse(503, 'SERVICE_UNAVAILABLE'),
      'GET /api/v1/reports/money-due': failingRoute,
      'GET /api/v1/reports/suggested-actions': () => problemResponse(503, 'SERVICE_UNAVAILABLE'),
    });

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: 'Try again' }).length).toBe(3);
    });
    shouldFail = false;
    await userEvent.click(screen.getAllByRole('button', { name: 'Try again' })[1] ?? document.body);
    expect(await screen.findByRole('button', { name: /Money due from brands/ })).toBeTruthy();
  });

  it('shows a calm error with retry when the funnel does not load', async () => {
    renderSalesReport({
      'GET /api/v1/reports/funnel': () => problemResponse(500, 'INTERNAL_SERVER_ERROR'),
    });

    expect(await screen.findByText('Something did not load. Please try again.')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeTruthy();
  });

  it('shows M5 in the Tamil shop language', async () => {
    renderSalesReport();
    await waitForLoadedReport();

    await userEvent.click(
      within(screen.getByRole('navigation', { name: 'Main' })).getByRole('button', {
        name: 'தமிழ்',
      }),
    );

    expect(screen.getByRole('heading', { level: 1, name: 'விற்பனை அறிக்கை' })).toBeTruthy();
    expect(screen.getByText('மேலும் விற்க நீங்கள் செய்யக்கூடியவை')).toBeTruthy();
  });

  it('has no accessibility violations, with each panel open', async () => {
    const { container } = renderSalesReport();
    await waitForLoadedReport();
    await expectNoAccessibilityViolations(container);

    await userEvent.click(screen.getByRole('button', { name: /Missed sales/ }));
    await expectNoAccessibilityViolations(container);
    await userEvent.click(screen.getByRole('button', { name: /Money due from brands/ }));
    await expectNoAccessibilityViolations(container);
  });
});
