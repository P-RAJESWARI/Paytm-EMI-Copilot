import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { CustomerApiError } from '../../customer-flow';
import { DESIGN_PLAN_ANSWERS } from '../../../testing/customerFlowTestData';
import { prepareFixtureWithAnswers, renderCustomerFlow } from '../../../testing/renderCustomerFlow';

const EXPLANATION_STEP = { step: 'explanation', answers: DESIGN_PLAN_ANSWERS } as const;

afterEach(() => {
  window.localStorage.clear();
});

describe('C7 explanation', () => {
  it('shows the AI-written text, its two numbers, the AI note, Listen and the plan recap', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    const { container } = renderCustomerFlow({
      customerFlowApi,
      initialFlowState: EXPLANATION_STEP,
    });

    expect(
      await screen.findByText(/No-cost EMI from Brand: you pay ₹3,667 each month/),
    ).toBeTruthy();
    const highlights = screen.getByRole('list', { name: 'The two numbers to remember' });
    expect(
      within(highlights)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['₹3,667 a month', '₹0 extra in total']);
    expect(
      screen.getByText(
        'Written by AI to explain the plans. It does not decide for you or approve anything.',
      ),
    ).toBeTruthy();
    expect(screen.queryByText('Showing the standard plan details.')).toBeNull();
    const recap = within(screen.getByRole('region', { name: 'Plan you chose' }));
    expect(recap.getByText('₹22,000')).toBeTruthy();
    expect(recap.getByText('6 months')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Listen to this' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Check my understanding' })).toBeTruthy();
    await expectNoAccessibilityViolations(container);
  });

  it('fetches the Tamil text when the customer switches language', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    const explainPlan = vi.spyOn(customerFlowApi, 'explainPlan');
    renderCustomerFlow({ customerFlowApi, initialFlowState: EXPLANATION_STEP });
    await screen.findByText(/No-cost EMI from Brand/);

    await userEvent.click(screen.getByRole('button', { name: 'தமிழ்' }));

    expect(await screen.findByText(/கட்டணமில்லா EMI: 6 மாதங்களுக்கு/)).toBeTruthy();
    expect(explainPlan).toHaveBeenLastCalledWith('mock-offer-no-cost-6m', 'ta');
    expect(screen.getByText('மாதம் ₹3,667')).toBeTruthy();
  });

  it('shows no error banner when the text is unavailable: the recap keeps every number', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    vi.spyOn(customerFlowApi, 'explainPlan').mockRejectedValue(
      new CustomerApiError(502, 'EXPLANATION_UNAVAILABLE', { hasProblemBody: true }),
    );
    renderCustomerFlow({ customerFlowApi, initialFlowState: EXPLANATION_STEP });

    expect(await screen.findByText('Showing the standard plan details.')).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
    const recap = within(screen.getByRole('region', { name: 'Plan you chose' }));
    expect(recap.getByText('₹3,667')).toBeTruthy();
    expect(recap.getByText('₹0')).toBeTruthy();
  });

  it('shows a skeleton while the text loads, with the recap already there', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    vi.spyOn(customerFlowApi, 'explainPlan').mockReturnValue(new Promise(() => undefined));

    renderCustomerFlow({ customerFlowApi, initialFlowState: EXPLANATION_STEP });

    expect(await screen.findByRole('status', { name: 'Getting the explanation' })).toBeTruthy();
    expect(screen.getByRole('region', { name: 'Plan you chose' })).toBeTruthy();
  });

  it('continues to confirm', async () => {
    const customerFlowApi = await prepareFixtureWithAnswers();
    renderCustomerFlow({ customerFlowApi, initialFlowState: EXPLANATION_STEP });

    await userEvent.click(await screen.findByRole('button', { name: 'Continue to confirm' }));

    expect(screen.queryByRole('heading', { name: 'Your plan in plain words' })).toBeNull();
  });
});
