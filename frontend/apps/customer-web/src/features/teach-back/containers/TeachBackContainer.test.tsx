import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import { CustomerApiError } from '../../customer-flow';
import { DESIGN_PLAN_ANSWERS } from '../../../testing/customerFlowTestData';
import { installFakeMicrophone, removeFakeMicrophone } from '../../../testing/fakeMicrophone';
import { prepareFixtureWithAnswers, renderCustomerFlow } from '../../../testing/renderCustomerFlow';

const TEACH_BACK_STEP = { step: 'teachBack', answers: DESIGN_PLAN_ANSWERS } as const;
const TITLE = 'Tell us in your own words what you will pay each month.';

afterEach(() => {
  removeFakeMicrophone();
  window.localStorage.clear();
});

// Opens C8 on the fixture, already past C2 and C3, and waits for the lazily loaded screen.
async function renderTeachBack() {
  const customerFlowApi = await prepareFixtureWithAnswers();
  const { container } = renderCustomerFlow({
    customerFlowApi,
    initialFlowState: TEACH_BACK_STEP,
  });
  await screen.findByRole('heading', { name: TITLE });
  return { customerFlowApi, container };
}

// Types an answer into C8 and asks for the check.
async function typeAndCheck(answerText: string): Promise<void> {
  await userEvent.type(screen.getByRole('textbox', { name: 'Your answer' }), answerText);
  await userEvent.click(screen.getByRole('button', { name: 'Check my answer' }));
}

describe('C8 teach-back', () => {
  it('shows the plan, an empty answer and Check disabled until something is typed', async () => {
    const { container } = await renderTeachBack();

    expect(screen.getByText('No-cost EMI, 6 months')).toBeTruthy();
    expect(screen.getByRole('textbox', { name: 'Your answer' })).toHaveProperty(
      'placeholder',
      'For example: I pay … every month for … months',
    );
    expect(screen.getByRole('button', { name: 'Check my answer' })).toHaveProperty(
      'disabled',
      true,
    );
    await expectNoAccessibilityViolations(container);
  });

  it('says CLOSE_ENOUGH answers are right, with the plan numbers, and continues to consent', async () => {
    const { customerFlowApi, container } = await renderTeachBack();
    const checkTeachBack = vi.spyOn(customerFlowApi, 'checkTeachBack');

    await typeAndCheck('I pay 3,667 every month for 6 months');

    expect(await screen.findByRole('heading', { name: 'That is right' })).toBeTruthy();
    expect(checkTeachBack).toHaveBeenCalledWith(
      'mock-offer-no-cost-6m',
      'I pay 3,667 every month for 6 months',
      'en',
    );
    const numbers = screen.getByRole('list', { name: 'The numbers to remember' });
    expect(
      within(numbers)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['₹3,667 a month', 'Extra ₹0']);
    expect(screen.queryByRole('button', { name: 'Explain it again' })).toBeNull();
    await expectNoAccessibilityViolations(container);

    await userEvent.click(screen.getByRole('button', { name: 'Continue' }));
    expect(
      await screen.findByRole('heading', { name: 'Check and confirm your plan' }),
    ).toBeTruthy();
  });

  it('says TRY_AGAIN calmly with what was heard, and "Explain it again" returns to C7', async () => {
    const { container } = await renderTeachBack();

    await typeAndCheck('About 3000 every month');

    expect(await screen.findByRole('heading', { name: 'Nearly there' })).toBeTruthy();
    expect(screen.getByText('About 3000 every month', { selector: 'span' })).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
    await expectNoAccessibilityViolations(container);

    await userEvent.click(screen.getByRole('button', { name: 'Explain it again' }));
    expect(await screen.findByRole('heading', { name: 'Your plan in plain words' })).toBeTruthy();
  });

  it('lets the customer skip straight to consent', async () => {
    await renderTeachBack();

    await userEvent.click(screen.getByRole('button', { name: 'Skip this step' }));

    expect(
      await screen.findByRole('heading', { name: 'Check and confirm your plan' }),
    ).toBeTruthy();
  });

  it('fills the answer from the microphone transcript for the customer to check', async () => {
    installFakeMicrophone();
    const { customerFlowApi } = await renderTeachBack();
    const transcribeSpeech = vi.spyOn(customerFlowApi, 'transcribeSpeech');

    await userEvent.click(screen.getByRole('button', { name: 'Or tap and say it' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Listening. Tap to stop.' }));

    expect(await screen.findByDisplayValue('I pay 3,667 every month for 6 months')).toBeTruthy();
    expect(transcribeSpeech).toHaveBeenCalledWith(expect.any(Blob), 'TEACH_BACK');
  });

  it('says calmly that the check did not work, and still lets the customer continue', async () => {
    const { customerFlowApi } = await renderTeachBack();
    vi.spyOn(customerFlowApi, 'checkTeachBack').mockRejectedValue(
      new CustomerApiError(502, 'AI_UNAVAILABLE', { hasProblemBody: true }),
    );

    await typeAndCheck('I pay 3,667');

    expect(
      await screen.findByText('We could not check that just now. You can still continue.'),
    ).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByRole('button', { name: 'Continue' })).toHaveProperty('disabled', false);
  });

  it('goes back to C7 from the back button', async () => {
    await renderTeachBack();

    await userEvent.click(screen.getByRole('button', { name: 'Back' }));

    expect(await screen.findByRole('heading', { name: 'Your plan in plain words' })).toBeTruthy();
  });
});
