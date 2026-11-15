import { describe, expect, it } from 'vitest';

import { FixtureCustomerFlowApi } from './FixtureCustomerFlowApi';
import {
  FIXTURE_CARD_PLAN,
  FIXTURE_CARDLESS_PLAN,
  FIXTURE_NO_COST_PLAN,
  FIXTURE_OTP,
} from './fixtureCustomerFlowData';

const DESIGN_BUDGET_IN_PAISE = 300000;
const NOTHING_FITS_BUDGET_IN_PAISE = 180000;
const START_TIME = Date.parse('2026-11-15T09:30:00Z');

/** The figures C9 shows for plan A. */
const PLAN_A_SUBMISSION = {
  offerId: FIXTURE_NO_COST_PLAN.offerId,
  shownMonthlyInstallmentInPaise: FIXTURE_NO_COST_PLAN.monthlyInstallmentInPaise,
  shownTotalPayableInPaise: FIXTURE_NO_COST_PLAN.totalPayableInPaise,
  otp: FIXTURE_OTP,
};

// Builds a fixture with a movable clock, a session, the given budget and a completed comfort check.
async function createFixtureUpToPlans(monthlyBudgetInPaise = DESIGN_BUDGET_IN_PAISE) {
  const clock = { now: START_TIME };
  const fixture = new FixtureCustomerFlowApi({
    now: () => clock.now,
    receiptStatuses: ['READY_TO_PAY', 'PAYMENT_PENDING', 'PAID'],
  });
  await fixture.startSession('qr-1');
  await fixture.confirmBudget(monthlyBudgetInPaise);
  await fixture.answerComfortCheck(true);
  return { fixture, clock };
}

describe('FixtureCustomerFlowApi: session and plans', () => {
  it('opens a session once per QR token and never hands out the session token', async () => {
    const fixture = new FixtureCustomerFlowApi();

    const session = await fixture.startSession('qr-1');

    expect(session).toMatchObject({ shopName: 'Ravi Electronics', priceInPaise: 2200000 });
    expect(session).not.toHaveProperty('sessionToken');
    await expect(fixture.startSession('qr-1')).rejects.toMatchObject({
      code: 'CUSTOMER_QR_TOKEN_INVALID',
    });
    await expect(fixture.startSession('')).rejects.toMatchObject({ status: 401 });
  });

  it('needs a session, then a budget, before anything else', async () => {
    const fixture = new FixtureCustomerFlowApi();

    await expect(fixture.confirmBudget(DESIGN_BUDGET_IN_PAISE)).rejects.toMatchObject({
      code: 'CUSTOMER_SESSION_TOKEN_INVALID',
    });
    await fixture.startSession('qr-1');
    await expect(fixture.listPlans()).rejects.toMatchObject({ code: 'BUDGET_NOT_CONFIRMED' });
  });

  it('ranks the design plans with bands after a completed check', async () => {
    const { fixture } = await createFixtureUpToPlans();

    const comparison = await fixture.listPlans();

    expect(comparison.hasComfortCheck).toBe(true);
    expect(comparison.plans.map((plan) => plan.offerId)).toEqual([
      FIXTURE_CARDLESS_PLAN.offerId,
      FIXTURE_NO_COST_PLAN.offerId,
      FIXTURE_CARD_PLAN.offerId,
    ]);
    expect(comparison.plans.map((plan) => plan.comfort?.comfortRatioInBasisPoints)).toEqual([
      3350, 3889, 3950,
    ]);
  });

  it('lists every plan above the budget at ₹1,800, and shows no bands after a skip', async () => {
    const fixture = new FixtureCustomerFlowApi();
    await fixture.startSession('qr-1');
    await fixture.confirmBudget(NOTHING_FITS_BUDGET_IN_PAISE);
    await fixture.answerComfortCheck(false);

    const comparison = await fixture.listPlans();

    expect(comparison.hasAnyPlanWithinBudget).toBe(false);
    expect(comparison.hasComfortCheck).toBe(false);
    expect(comparison.plans).toHaveLength(3);
    expect(comparison.plans.every((plan) => !plan.isWithinBudget && plan.comfort === null)).toBe(
      true,
    );
  });
});

describe('FixtureCustomerFlowApi: alternatives and explanation', () => {
  it('gives the engine figures for plan A (₹3,000 a month at 3,667 bp, ADR 0020)', async () => {
    const { fixture } = await createFixtureUpToPlans();

    const alternatives = await fixture.findAlternatives(FIXTURE_NO_COST_PLAN.offerId);

    expect(alternatives.alternatives.map((alternative) => alternative.kind)).toEqual([
      'DOWN_PAYMENT',
      'LONGER_TENURE',
      'CHEAPER_MODEL',
    ]);
    expect(alternatives.alternatives[0]).toMatchObject({
      monthlyInstallmentInPaise: 300000,
      comfort: { comfortRatioInBasisPoints: 3667 },
    });
  });

  it('answers "nothing better" for other plans, hides bands after a skip and refuses unknown offers', async () => {
    const fixture = new FixtureCustomerFlowApi();
    await fixture.startSession('qr-1');
    await fixture.confirmBudget(DESIGN_BUDGET_IN_PAISE);
    await fixture.answerComfortCheck(false);

    const forCardless = await fixture.findAlternatives(FIXTURE_CARDLESS_PLAN.offerId);
    const forPlanA = await fixture.findAlternatives(FIXTURE_NO_COST_PLAN.offerId);

    expect(forCardless).toMatchObject({ hasLowerMonthlyAlternative: false, alternatives: [] });
    expect(forCardless.basePlan).not.toHaveProperty('position');
    expect(forPlanA.basePlan.comfort).toBeNull();
    expect(forPlanA.alternatives.every((alternative) => alternative.comfort === null)).toBe(true);
    await expect(fixture.findAlternatives('unknown-offer')).rejects.toMatchObject({
      code: 'OFFER_NOT_FOUND',
    });
  });

  it('explains a plan in the asked language with its two highlighted amounts', async () => {
    const { fixture } = await createFixtureUpToPlans();

    const explanation = await fixture.explainPlan(FIXTURE_CARD_PLAN.offerId, 'ta');

    expect(explanation.language).toBe('ta');
    expect(explanation.text).toContain('₹3,850');
    expect(explanation.highlightedAmounts).toEqual([
      { kind: 'MONTHLY_INSTALLMENT', amountInPaise: 385000 },
      { kind: 'EXTRA_IN_TOTAL', amountInPaise: 110000 },
    ]);
  });
});

describe('FixtureCustomerFlowApi: OTP and consent', () => {
  it('limits resends to one per 30 seconds and refuses consent before an OTP', async () => {
    const { fixture, clock } = await createFixtureUpToPlans();

    await expect(fixture.giveConsent(PLAN_A_SUBMISSION, 'key-0')).rejects.toMatchObject({
      code: 'OTP_NOT_REQUESTED',
    });
    const challenge = await fixture.requestConsentOtp();
    clock.now += 6000;

    expect(challenge).toMatchObject({ phoneLastTwoDigits: '42', attemptsRemaining: 3 });
    expect(challenge.resendAvailableAt).toBe('2026-11-15T09:30:30.000Z');
    await expect(fixture.requestConsentOtp()).rejects.toMatchObject({
      status: 429,
      retryAfterInSeconds: 24,
    });
    clock.now += 24000;
    await expect(fixture.requestConsentOtp()).resolves.toMatchObject({ attemptsRemaining: 3 });
  });

  it('counts wrong tries down and spends the OTP on the third (OTP_EXPIRED)', async () => {
    const { fixture } = await createFixtureUpToPlans();
    await fixture.requestConsentOtp();
    const wrongSubmission = { ...PLAN_A_SUBMISSION, otp: '000000' };

    await expect(fixture.giveConsent(wrongSubmission, 'key-1')).rejects.toMatchObject({
      code: 'OTP_INCORRECT',
      attemptsRemaining: 2,
    });
    await expect(fixture.giveConsent(wrongSubmission, 'key-2')).rejects.toMatchObject({
      attemptsRemaining: 1,
    });
    await expect(fixture.giveConsent(wrongSubmission, 'key-3')).rejects.toMatchObject({
      code: 'OTP_EXPIRED',
    });
    await expect(fixture.giveConsent(PLAN_A_SUBMISSION, 'key-4')).rejects.toMatchObject({
      code: 'OTP_EXPIRED',
    });
  });

  it('expires the OTP after five minutes and refuses changed figures', async () => {
    const { fixture, clock } = await createFixtureUpToPlans();
    await fixture.requestConsentOtp();

    await expect(
      fixture.giveConsent({ ...PLAN_A_SUBMISSION, shownTotalPayableInPaise: 1 }, 'key-1'),
    ).rejects.toMatchObject({ status: 409, code: 'SHOWN_PLAN_CHANGED' });
    await expect(
      fixture.giveConsent({ ...PLAN_A_SUBMISSION, shownMonthlyInstallmentInPaise: 1 }, 'key-2'),
    ).rejects.toMatchObject({ code: 'SHOWN_PLAN_CHANGED' });
    clock.now += 5 * 60 * 1000;
    await expect(fixture.giveConsent(PLAN_A_SUBMISSION, 'key-3')).rejects.toMatchObject({
      code: 'OTP_EXPIRED',
    });
  });

  it('records consent once, replays the same key and moves the receipt through its statuses', async () => {
    const { fixture } = await createFixtureUpToPlans();
    await expect(fixture.getReceipt()).rejects.toMatchObject({ code: 'CONSENT_NOT_GIVEN' });
    await fixture.requestConsentOtp();

    const confirmation = await fixture.giveConsent(PLAN_A_SUBMISSION, 'key-1');

    expect(confirmation).toMatchObject({ reference: 'EMI-2611-0042', status: 'READY_TO_PAY' });
    expect(confirmation.plan.regularInstallmentInPaise).toBe(366667);
    await expect(fixture.giveConsent(PLAN_A_SUBMISSION, 'key-1')).resolves.toBe(confirmation);
    await expect(fixture.giveConsent(PLAN_A_SUBMISSION, 'key-2')).rejects.toMatchObject({
      code: 'CONSENT_ALREADY_GIVEN',
    });
    const statuses = [];
    for (let readIndex = 0; readIndex < 4; readIndex += 1) {
      statuses.push((await fixture.getReceipt()).status);
    }
    expect(statuses).toEqual(['READY_TO_PAY', 'PAYMENT_PENDING', 'PAID', 'PAID']);
  });
});
