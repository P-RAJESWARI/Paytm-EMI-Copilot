import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { CustomerApiError } from '../../customer-flow';
import { DESIGN_ANSWERS, plansStep, SKIPPED_ANSWERS } from '../../../testing/customerFlowTestData';
import { prepareFixtureWithAnswers, renderCustomerFlow } from '../../../testing/renderCustomerFlow';

// Renders C4 on a fixture already past C2 and C3 with the given answers.
async function renderPlans(options: Parameters<typeof prepareFixtureWithAnswers>[0] = {}) {
  const customerFlowApi = await prepareFixtureWithAnswers(options);
  const answers = {
    confirmedBudgetInPaise: options.monthlyBudgetInPaise ?? DESIGN_ANSWERS.confirmedBudgetInPaise,
    comfortCheck:
      options.hasCustomerConsentedToComfortCheck === false
        ? SKIPPED_ANSWERS.comfortCheck
        : DESIGN_ANSWERS.comfortCheck,
  };
  return renderCustomerFlow({ customerFlowApi, initialFlowState: plansStep(answers) });
}

// Gives the plan card (article) whose radio has this accessible name.
function planCard(radioName: string): HTMLElement {
  const card = screen.getByRole('radio', { name: radioName }).closest('article');
  if (card === null) throw new Error(`No card for ${radioName}`);
  return card;
}

afterEach(() => {
  window.localStorage.clear();
});

describe('C4 options comparison: loaded', () => {
  it('lists every plan in the server order with monthly and extra in total at the same size', async () => {
    const { container } = await renderPlans();

    const radios = await screen.findAllByRole('radio');
    expect(radios.map((radio) => radio.closest('label')?.textContent)).toEqual([
      'EMI Demo cardless lender (Mock), 12 months',
      'No-cost EMI Brand, 6 months',
      "EMI Your card's bank, 6 months",
    ]);
    const noCostCard = within(planCard('No-cost EMI Brand, 6 months'));
    const monthlyValue = noCostCard.getByText('₹3,667');
    const extraValue = noCostCard.getByText('₹0');
    expect(monthlyValue.className).toBe(extraValue.className);
    expect(noCostCard.getByText('for 6 months')).toBeTruthy();
    expect(noCostCard.getByText('on top of ₹22,000')).toBeTruthy();
    expect(noCostCard.getByText('₹667 above your budget')).toBeTruthy();
    expect(noCostCard.getByText('You pay in all ₹22,000')).toBeTruthy();
    await expectNoAccessibilityViolations(container);
  });

  it('shows each band as icon and word, the sort note and the trade-off note', async () => {
    await renderPlans();

    await screen.findAllByRole('radio');
    const cardlessCard = within(planCard('EMI Demo cardless lender (Mock), 12 months'));
    const bandWord = cardlessCard.getByText('Comfortable');
    expect(bandWord.querySelector('svg[aria-hidden="true"]')).not.toBeNull();
    expect(cardlessCard.getByText('Within your budget')).toBeTruthy();
    expect(screen.getByText('Sorted by what fits your ₹3,000 budget')).toBeTruthy();
    expect(
      screen.getByText(/The plan with nothing extra has a higher monthly amount\./),
    ).toBeTruthy();
    expect(screen.getByText('Example phone, 128 GB, ₹22,000')).toBeTruthy();
  });

  it('selects nothing for the customer; Continue opens once a plan is chosen', async () => {
    await renderPlans();
    await screen.findAllByRole('radio');
    const continueButton = screen.getByRole('button', { name: 'Continue' });

    expect(continueButton).toHaveProperty('disabled', true);
    expect(screen.getByText('Choose a plan to continue.')).toBeTruthy();
    expect(
      screen.getAllByRole('radio').every((radio) => !(radio as HTMLInputElement).checked),
    ).toBe(true);
    await userEvent.click(screen.getByRole('radio', { name: 'No-cost EMI Brand, 6 months' }));

    expect(continueButton).toHaveProperty('disabled', false);
    await userEvent.click(continueButton);
    expect(screen.queryByRole('heading', { name: 'Your EMI options' })).toBeNull();
  });

  it('opens the comfort detail and comes back with the selection kept', async () => {
    await renderPlans();
    await userEvent.click(
      await screen.findByRole('radio', { name: 'No-cost EMI Brand, 6 months' }),
    );

    await userEvent.click(
      within(planCard("EMI Your card's bank, 6 months")).getByRole('button', {
        name: 'Comfort detail for EMI, 6 months',
      }),
    );
    expect(screen.getByRole('heading', { name: 'Comfort detail' })).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: 'Back to plans' }));

    expect(
      await screen.findByRole('radio', { name: 'No-cost EMI Brand, 6 months' }),
    ).toHaveProperty('checked', true);
  });
});

describe('C4 options comparison: other states', () => {
  it('keeps every plan when none fits ₹1,800, each labelled above the budget', async () => {
    const { container } = await renderPlans({ monthlyBudgetInPaise: 180000 });

    expect(
      await screen.findByRole('heading', { name: 'No plan is within ₹1,800 a month' }),
    ).toBeTruthy();
    expect(screen.getAllByRole('radio')).toHaveLength(3);
    expect(screen.getAllByText(/above your budget/)).toHaveLength(3);
    expect(screen.getByText('₹250 above your budget')).toBeTruthy();
    expect(screen.getByText('Sorted by what is closest to your ₹1,800 budget')).toBeTruthy();
    expect(
      screen.getByText('Choose a plan below to see ways to lower its monthly amount.'),
    ).toBeTruthy();
    await expectNoAccessibilityViolations(container);
    await userEvent.click(screen.getByRole('radio', { name: 'No-cost EMI Brand, 6 months' }));
    await userEvent.click(
      screen.getByRole('button', { name: 'See ways to lower the monthly amount' }),
    );

    expect(screen.queryByRole('heading', { name: 'Your EMI options' })).toBeNull();
  });

  it('shows no band and no comfort detail after a skipped check', async () => {
    await renderPlans({ hasCustomerConsentedToComfortCheck: false });

    expect(await screen.findAllByRole('radio')).toHaveLength(3);
    expect(screen.queryByText(/Comfortable|Stretching|Risky/)).toBeNull();
    expect(screen.queryByRole('button', { name: /Comfort detail/ })).toBeNull();
  });

  it('shows a skeleton while the plans load', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    vi.spyOn(customerFlowApi, 'listPlans').mockReturnValue(new Promise(() => undefined));

    renderCustomerFlow({ customerFlowApi, initialFlowState: plansStep() });

    expect(
      await screen.findByRole('status', { name: 'Getting plans for this phone' }),
    ).toBeTruthy();
  });

  it('shows a calm error with a retry when the plans could not be fetched', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    vi.spyOn(customerFlowApi, 'listPlans').mockRejectedValueOnce(
      new CustomerApiError(504, 'PAYMENT_GATEWAY_TIMEOUT', { hasProblemBody: true }),
    );
    renderCustomerFlow({ customerFlowApi, initialFlowState: plansStep() });

    expect((await screen.findByRole('alert')).textContent).toContain(
      'The plans are taking too long to arrive.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findAllByRole('radio')).toHaveLength(3);
  });

  it('says so calmly when no plan is offered', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    vi.spyOn(customerFlowApi, 'listPlans').mockResolvedValue({
      monthlyBudgetInPaise: 300000,
      hasAnyPlanWithinBudget: false,
      hasComfortCheck: true,
      plans: [],
    });

    const { container } = renderCustomerFlow({ customerFlowApi, initialFlowState: plansStep() });

    expect(
      await screen.findByText(
        'No EMI plans are offered for this item right now. Please ask the shop.',
      ),
    ).toBeTruthy();
    await expectNoAccessibilityViolations(container);
  });

  it('says the figures changed after consent found a change, and reads in Tamil', async () => {
    window.localStorage.setItem('emiCopilot.language', 'ta');
    const customerFlowApi = await prepareFixtureWithAnswers();

    renderCustomerFlow({ customerFlowApi, initialFlowState: plansStep(DESIGN_ANSWERS, true) });

    expect(await screen.findByText('பட்ஜெட்டை விட ₹667 அதிகம்')).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'உங்கள் EMI வாய்ப்புகள்' })).toBeTruthy();
    expect(screen.getByRole('status').textContent).toContain('எண்கள் மாறிவிட்டன');
    expect(screen.getByRole('radio', { name: 'கட்டணமில்லா EMI Brand, 6 மாதங்கள்' })).toBeTruthy();
  });

  it('goes back to the comfort check question', async () => {
    await renderPlans();

    await userEvent.click(await screen.findByRole('button', { name: 'Back' }));

    expect(screen.getByRole('heading', { name: 'Check if a plan fits your month?' })).toBeTruthy();
  });
});
