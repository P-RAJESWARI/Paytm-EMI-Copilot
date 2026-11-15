import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { expectNoAccessibilityViolations } from '@test-support/accessibility';

import {
  FIXTURE_CARD_PLAN,
  FIXTURE_CARDLESS_PLAN,
  FIXTURE_COMFORT_CHECK_COMPLETED,
} from '../../customer-flow/api/fixtureCustomerFlowData';
import { initializeCustomerI18n } from '../../../i18n/initializeCustomerI18n';
import { DESIGN_ANSWERS } from '../../../testing/customerFlowTestData';
import { renderCustomerFlow } from '../../../testing/renderCustomerFlow';
import { ComfortDetailScreen } from '../components/ComfortDetailScreen';

/** The design's Risky example: inflow ₹20,000, existing EMIs ₹8,000, plan B (ADR 0020). */
const RISKY_CARD_PLAN = {
  ...FIXTURE_CARD_PLAN,
  comfort: {
    band: 'RISKY',
    comfortRatioInBasisPoints: 5925,
    planShareInBasisPoints: 1925,
    existingEmisShareInBasisPoints: 4000,
  },
} as const;

afterEach(() => {
  window.localStorage.clear();
});

describe('C5 comfort detail', () => {
  it('explains plan B: Stretching, 39.5% with this plan, 26.7% already, and the amounts', async () => {
    const { container } = renderCustomerFlow({
      initialFlowState: {
        step: 'comfortDetail',
        answers: DESIGN_ANSWERS,
        detailPlan: FIXTURE_CARD_PLAN,
        selectedPlan: undefined,
      },
    });

    expect(await screen.findByRole('heading', { name: 'Comfort detail' })).toBeTruthy();
    expect(screen.getByText('Stretching')).toBeTruthy();
    expect(
      screen.getByText('With this plan, your EMIs take 39.5% of your monthly inflow.'),
    ).toBeTruthy();
    expect(screen.getByText('Your current EMIs already take 26.7%.')).toBeTruthy();
    expect(screen.getByText('₹8,000 (26.7%)')).toBeTruthy();
    expect(screen.getByText('₹3,850 (12.8%)')).toBeTruthy();
    expect(screen.getByText('₹30,000')).toBeTruthy();
    expect(
      screen.getByRole('img', { name: 'EMIs you pay now 26.7%, with this plan 39.5%' }),
    ).toBeTruthy();
    expect(screen.getByText('A guide to help you choose, not a loan decision.')).toBeTruthy();
    await expectNoAccessibilityViolations(container);
  });

  it('shows the Comfortable band for the cardless plan', async () => {
    renderCustomerFlow({
      initialFlowState: {
        step: 'comfortDetail',
        answers: DESIGN_ANSWERS,
        detailPlan: FIXTURE_CARDLESS_PLAN,
        selectedPlan: undefined,
      },
    });

    expect(await screen.findByText('Comfortable')).toBeTruthy();
    expect(screen.getByText('₹2,050 (6.8%)')).toBeTruthy();
  });

  it('shows the Risky band in words and icon for the design risky example', async () => {
    const onBack = vi.fn();
    const { container } = render(
      <I18nextProvider i18n={initializeCustomerI18n()}>
        <ComfortDetailScreen
          plan={RISKY_CARD_PLAN}
          comfortCheck={{ ...FIXTURE_COMFORT_CHECK_COMPLETED, monthlyInflowInPaise: 2000000 }}
          onBack={onBack}
        />
      </I18nextProvider>,
    );

    const riskyChip = screen.getByText('Risky');
    expect(riskyChip.querySelector('svg[data-band-icon="risky"]')).not.toBeNull();
    expect(screen.getByText(/59\.3%/)).toBeTruthy();
    expect(screen.getByText('₹8,000 (40%)')).toBeTruthy();
    expect(screen.getByText('₹20,000')).toBeTruthy();
    await expectNoAccessibilityViolations(container);
  });

  it('shows the shares alone when the amounts are not available', () => {
    render(
      <I18nextProvider i18n={initializeCustomerI18n()}>
        <ComfortDetailScreen
          plan={RISKY_CARD_PLAN}
          comfortCheck={{
            ...FIXTURE_COMFORT_CHECK_COMPLETED,
            existingEmisInPaise: null,
            monthlyInflowInPaise: null,
          }}
          onBack={() => undefined}
        />
      </I18nextProvider>,
    );

    expect(screen.getByText('40%')).toBeTruthy();
    expect(screen.queryByText('Money coming in each month')).toBeNull();
  });

  it('shows nothing for a plan without a comfort result', () => {
    const { container } = renderCustomerFlow({
      initialFlowState: {
        step: 'comfortDetail',
        answers: DESIGN_ANSWERS,
        detailPlan: { ...FIXTURE_CARD_PLAN, comfort: null },
        selectedPlan: undefined,
      },
    });

    expect(container.querySelector('h1')).toBeNull();
  });
});
