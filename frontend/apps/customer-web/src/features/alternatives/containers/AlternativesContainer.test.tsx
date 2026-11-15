import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { CustomerApiError } from '../../customer-flow';
import { FIXTURE_CARDLESS_PLAN } from '../../customer-flow/api/fixtureCustomerFlowData';
import { DESIGN_PLAN_ANSWERS } from '../../../testing/customerFlowTestData';
import { prepareFixtureWithAnswers, renderCustomerFlow } from '../../../testing/renderCustomerFlow';

const ALTERNATIVES_STEP = { step: 'alternatives', answers: DESIGN_PLAN_ANSWERS } as const;

// Renders C6 for plan A on a fixture past C2 and C3.
async function renderAlternatives() {
  const customerFlowApi = await prepareFixtureWithAnswers();
  return renderCustomerFlow({ customerFlowApi, initialFlowState: ALTERNATIVES_STEP });
}

// Gives the selected alternative's card once a chip was pressed.
function selectedAlternativeCard(): HTMLElement {
  const cards = screen.getAllByRole('region');
  const card = cards.at(-1);
  if (card === undefined) throw new Error('No alternative card');
  return card;
}

afterEach(() => {
  window.localStorage.clear();
});

describe('C6 smarter alternatives', () => {
  it('shows the plan being looked at, with its band, share and budget gap', async () => {
    const { container } = await renderAlternatives();

    expect(
      await screen.findByText(
        'Stretching, 38.9% of monthly inflow. ₹667 above your ₹3,000 budget.',
      ),
    ).toBeTruthy();
    expect(screen.getByText('No-cost EMI, 6 months')).toBeTruthy();
    expect(
      screen.getAllByRole('button', { pressed: false }).map((chip) => chip.textContent),
    ).toEqual(
      expect.arrayContaining(['Add a ₹4,000 down payment', 'Longer tenure', 'Cheaper model']),
    );
    expect(screen.getByText('Nothing is chosen until you confirm on the last step.')).toBeTruthy();
    await expectNoAccessibilityViolations(container);
  });

  it('shows the engine figures for a ₹4,000 down payment and sends the customer to the shop', async () => {
    const { container } = await renderAlternatives();

    await userEvent.click(await screen.findByRole('button', { name: 'Add a ₹4,000 down payment' }));

    const card = within(selectedAlternativeCard());
    expect(card.getByRole('heading', { name: 'No-cost EMI, 6 months, ₹4,000 down' })).toBeTruthy();
    expect(card.getByText('₹3,000')).toBeTruthy();
    expect(card.getByText('Was ₹3,667')).toBeTruthy();
    expect(card.getByText('Stretching').textContent).toBe('Stretching 36.7%');
    expect(card.getByText('You pay ₹4,000 at the shop, then ₹3,000 a month.')).toBeTruthy();
    expect(card.getByText('Ask the shop to set this up')).toBeTruthy();
    expect(card.queryByRole('button', { name: 'Choose this plan' })).toBeNull();
    expect(screen.queryByText(/2,999|36\.6%/)).toBeNull();
    await expectNoAccessibilityViolations(container);
  });

  it('names the cheaper model with its price and asks the shop to start a new sale', async () => {
    await renderAlternatives();

    await userEvent.click(await screen.findByRole('button', { name: 'Cheaper model' }));

    const card = within(selectedAlternativeCard());
    expect(card.getByRole('heading', { name: 'Example phone, 64 GB, ₹18,000' })).toBeTruthy();
    expect(card.getByText('No-cost EMI, 6 months on the smaller model.')).toBeTruthy();
    expect(
      card.getByText('The shop starts a new sale for this model and shows you a new QR.'),
    ).toBeTruthy();
  });

  it('lets the customer choose the longer tenure, which becomes the plan looked at', async () => {
    await renderAlternatives();
    await userEvent.click(await screen.findByRole('button', { name: 'Longer tenure' }));
    const card = within(selectedAlternativeCard());

    expect(card.getByRole('heading', { name: 'EMI, 12 months' })).toBeTruthy();
    expect(card.getByText('It costs ₹2,600 extra in total.')).toBeTruthy();
    expect(card.getByText('Comfortable').textContent).toBe('Comfortable 33.5%');
    await userEvent.click(card.getByRole('button', { name: 'Choose this plan' }));

    expect(await screen.findByText('EMI, 12 months')).toBeTruthy();
    expect(
      await screen.findByText('No other way lowers the monthly amount for this plan.'),
    ).toBeTruthy();
  });

  it("hides a chip's numbers when it is pressed again", async () => {
    await renderAlternatives();
    const longerTenureChip = await screen.findByRole('button', { name: 'Longer tenure' });

    await userEvent.click(longerTenureChip);
    await userEvent.click(longerTenureChip);

    expect(longerTenureChip.getAttribute('aria-pressed')).toBe('false');
    expect(screen.queryByText('It costs ₹2,600 extra in total.')).toBeNull();
  });

  it('shows the nothing-better state for a plan with no cheaper way', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();

    renderCustomerFlow({
      customerFlowApi,
      initialFlowState: {
        step: 'alternatives',
        answers: { ...DESIGN_PLAN_ANSWERS, selectedPlan: FIXTURE_CARDLESS_PLAN },
      },
    });

    expect(
      await screen.findByText('No other way lowers the monthly amount for this plan.'),
    ).toBeTruthy();
    expect(
      screen.getByText('Comfortable, 33.5% of monthly inflow. Within your ₹3,000 budget.'),
    ).toBeTruthy();
  });

  it('shows a skeleton while the alternatives load', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    vi.spyOn(customerFlowApi, 'findAlternatives').mockReturnValue(new Promise(() => undefined));

    renderCustomerFlow({ customerFlowApi, initialFlowState: ALTERNATIVES_STEP });

    expect(
      await screen.findByRole('status', { name: 'Finding ways to lower the monthly amount' }),
    ).toBeTruthy();
  });

  it('shows a calm retry when the alternatives could not be fetched', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    vi.spyOn(customerFlowApi, 'findAlternatives').mockRejectedValueOnce(
      new CustomerApiError(502, 'PAYMENT_GATEWAY_UNAVAILABLE', { hasProblemBody: true }),
    );
    renderCustomerFlow({ customerFlowApi, initialFlowState: ALTERNATIVES_STEP });

    expect((await screen.findByRole('alert')).textContent).toContain(
      'The plans could not be fetched just now.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('button', { name: 'Longer tenure' })).toBeTruthy();
  });

  it('continues to the explanation and goes back to the plans', async () => {
    await renderAlternatives();

    await userEvent.click(await screen.findByRole('button', { name: 'Continue' }));
    expect(screen.getByRole('heading', { name: 'Your plan in plain words' })).toBeTruthy();
    await userEvent.click(screen.getByRole('button', { name: 'Back' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Back' }));

    expect(
      await screen.findByRole('radio', { name: 'No-cost EMI Brand, 6 months' }),
    ).toHaveProperty('checked', true);
  });
});
