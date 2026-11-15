import { describe, expect, it } from 'vitest';

import {
  FIXTURE_CARD_PLAN,
  FIXTURE_CARDLESS_PLAN,
  FIXTURE_NO_COST_PLAN,
} from '../../customer-flow/api/fixtureCustomerFlowData';
import { hasMonthlyVersusTotalTradeOff } from './hasMonthlyVersusTotalTradeOff';

describe('hasMonthlyVersusTotalTradeOff', () => {
  it('is true when the no-extra plan and the lowest-monthly plan differ (the design data)', () => {
    expect(
      hasMonthlyVersusTotalTradeOff([
        FIXTURE_CARDLESS_PLAN,
        FIXTURE_NO_COST_PLAN,
        FIXTURE_CARD_PLAN,
      ]),
    ).toBe(true);
  });

  it('is false when one plan is both, or when either reason is missing', () => {
    const bothReasons = {
      ...FIXTURE_NO_COST_PLAN,
      reasonCodes: ['NO_EXTRA_COST', 'LOWEST_MONTHLY_AMOUNT'] as const,
    };

    expect(
      hasMonthlyVersusTotalTradeOff([
        { ...bothReasons, reasonCodes: [...bothReasons.reasonCodes] },
      ]),
    ).toBe(false);
    expect(hasMonthlyVersusTotalTradeOff([FIXTURE_CARDLESS_PLAN, FIXTURE_CARD_PLAN])).toBe(false);
    expect(hasMonthlyVersusTotalTradeOff([])).toBe(false);
  });
});
