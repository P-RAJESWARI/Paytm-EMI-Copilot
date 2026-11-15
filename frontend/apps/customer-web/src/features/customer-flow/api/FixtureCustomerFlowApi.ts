import type { SupportedLanguage } from '@emi-copilot/shared-i18n';

import {
  CUSTOMER_QR_TOKEN_INVALID_CODE,
  CUSTOMER_SESSION_TOKEN_INVALID_CODE,
  CustomerApiError,
} from './customerApiError';
import type { CustomerPlanResponse, ReceiptStatus } from './customerContractTypes';
import type {
  ComfortCheckResult,
  ConsentConfirmation,
  ConsentSubmission,
  CustomerFlowApi,
  CustomerReceipt,
  CustomerSession,
  OtpChallenge,
  PlanAlternatives,
  PlanComparison,
  PlanExplanation,
  SpeechPurpose,
  SpeechTranscription,
  TeachBackOutcome,
} from './CustomerFlowApi';
import {
  buildFixtureConsentedPlan,
  buildFixtureExplanation,
  FIXTURE_ALTERNATIVES_FOR_NO_COST_PLAN,
  FIXTURE_COMFORT_CHECK_COMPLETED,
  FIXTURE_COMFORT_CHECK_SKIPPED,
  FIXTURE_EXPLANATION_ID,
  FIXTURE_NO_COST_PLAN,
  FIXTURE_OTP,
  FIXTURE_PLANS_AT_DESIGN_BUDGET,
  FIXTURE_PLANS_WHEN_NOTHING_FITS,
  FIXTURE_RECEIPT_REFERENCE,
  FIXTURE_CUSTOMER_SESSION,
  toFixtureBasePlan,
} from './fixtureCustomerFlowData';
import {
  buildFixtureSilentWav,
  buildFixtureTeachBack,
  FIXTURE_TRANSCRIPTIONS,
} from './fixtureVoiceData';

/** Demo OTP rules from ADR 0022 decision 3: 3 tries, 5 minutes, resend after 30 seconds. */
const OTP_ATTEMPT_COUNT = 3;
const OTP_LIFETIME_IN_MILLISECONDS = 5 * 60 * 1000;
const OTP_RESEND_DELAY_IN_MILLISECONDS = 30 * 1000;
const MILLISECONDS_PER_SECOND = 1000;
/** The design's "no plan fits" budget (DESIGN_SPEC section 4); any other budget gets the ₹3,000 sample. */
const NOTHING_FITS_BUDGET_IN_PAISE = 180000;

/** The one OTP this fixture has sent, if any. */
interface IssuedOtp {
  expiresAtInMilliseconds: number;
  resendAvailableAtInMilliseconds: number;
  attemptsRemaining: number;
}

export interface FixtureCustomerFlowApiOptions {
  /** The clock, in milliseconds since 1970; tests pass a fixed one. */
  now?: (() => number) | undefined;
  /** Receipt statuses answered in turn (the last one repeats); defaults to READY_TO_PAY. */
  receiptStatuses?: readonly ReceiptStatus[] | undefined;
}

// Pattern: Fake (fixture adapter). Answers CustomerFlowApi from the DESIGN_SPEC section 4 sample
// in memory, with the contract's rules for QR reuse, OTP tries and changed figures. It is chosen
// only when VITE_CUSTOMER_FLOW_API=fixture, and in tests. Limit: it knows the ₹3,000 and ₹1,800
// design budgets; any other budget is answered with the ₹3,000 sample.
export class FixtureCustomerFlowApi implements CustomerFlowApi {
  private readonly now: () => number;
  private readonly receiptStatuses: readonly ReceiptStatus[];
  private readonly exchangedQrTokens = new Set<string>();
  private hasSession = false;
  private confirmedBudgetInPaise: number | undefined;
  private comfortCheck: ComfortCheckResult | undefined;
  private issuedOtp: IssuedOtp | undefined;
  private consent: { idempotencyKey: string; confirmation: ConsentConfirmation } | undefined;
  private receiptReadCount = 0;

  // Starts with no session, no answers and the given clock and receipt statuses.
  constructor({
    now = Date.now,
    receiptStatuses = ['READY_TO_PAY'],
  }: FixtureCustomerFlowApiOptions = {}) {
    this.now = now;
    this.receiptStatuses = receiptStatuses;
  }

  // Fails like the server when no session was opened on this phone.
  private requireSession(): void {
    if (!this.hasSession) throw new CustomerApiError(401, CUSTOMER_SESSION_TOKEN_INVALID_CODE);
  }

  // Fails like the server when a call needs the budget first.
  private requireBudget(): number {
    this.requireSession();
    if (this.confirmedBudgetInPaise === undefined) throw problem(409, 'BUDGET_NOT_CONFIRMED');
    return this.confirmedBudgetInPaise;
  }

  // Gives the plan as quoted now, without the comfort result when the check was not completed.
  private quotePlan(plan: CustomerPlanResponse): CustomerPlanResponse {
    return this.comfortCheck?.status === 'COMPLETED' ? plan : { ...plan, comfort: null };
  }

  // Exchanges a QR token once; a used or empty token is refused as the contract says.
  startSession(qrToken: string): Promise<CustomerSession> {
    if (qrToken === '' || this.exchangedQrTokens.has(qrToken)) {
      return Promise.reject(
        new CustomerApiError(401, CUSTOMER_QR_TOKEN_INVALID_CODE, { hasProblemBody: true }),
      );
    }
    this.exchangedQrTokens.add(qrToken);
    this.hasSession = true;
    return Promise.resolve(FIXTURE_CUSTOMER_SESSION);
  }

  // Keeps the confirmed budget; a new budget asks the comfort question again.
  confirmBudget(monthlyBudgetInPaise: number): Promise<void> {
    return settle(() => {
      this.requireSession();
      this.confirmedBudgetInPaise = monthlyBudgetInPaise;
      this.comfortCheck = undefined;
    });
  }

  // Gives the synthetic profile when allowed, or records the skip.
  answerComfortCheck(hasCustomerConsented: boolean): Promise<ComfortCheckResult> {
    return settle(() => {
      this.requireBudget();
      this.comfortCheck = hasCustomerConsented
        ? FIXTURE_COMFORT_CHECK_COMPLETED
        : FIXTURE_COMFORT_CHECK_SKIPPED;
      return this.comfortCheck;
    });
  }

  // Gives the sample ranking for the confirmed budget, with bands only after a completed check.
  listPlans(): Promise<PlanComparison> {
    return settle(() => {
      const ranking =
        this.requireBudget() === NOTHING_FITS_BUDGET_IN_PAISE
          ? FIXTURE_PLANS_WHEN_NOTHING_FITS
          : FIXTURE_PLANS_AT_DESIGN_BUDGET;
      return {
        ...ranking,
        hasComfortCheck: this.comfortCheck?.status === 'COMPLETED',
        plans: ranking.plans.map((plan) => this.quotePlan(plan)),
      };
    });
  }

  // Gives the sample alternatives for plan A and the "nothing better" answer for the others.
  findAlternatives(offerId: string): Promise<PlanAlternatives> {
    return settle(() => {
      const plan = this.findQuotedPlan(offerId);
      if (offerId === FIXTURE_NO_COST_PLAN.offerId) {
        const sample = FIXTURE_ALTERNATIVES_FOR_NO_COST_PLAN;
        const hasComfort = this.comfortCheck?.status === 'COMPLETED';
        return {
          ...sample,
          basePlan: { ...sample.basePlan, comfort: plan.comfort },
          alternatives: sample.alternatives.map((alternative) =>
            hasComfort ? alternative : { ...alternative, comfort: null },
          ),
        };
      }
      return {
        basePlan: toFixtureBasePlan(plan),
        hasLowerMonthlyAlternative: false,
        alternatives: [],
      };
    });
  }

  // Gives the template explanation of one plan in the asked language.
  explainPlan(offerId: string, language: SupportedLanguage): Promise<PlanExplanation> {
    return settle(() => buildFixtureExplanation(this.findQuotedPlan(offerId), language));
  }

  // Sends a new OTP unless the last one was sent under 30 seconds ago (then 429 with Retry-After).
  requestConsentOtp(): Promise<OtpChallenge> {
    return settle(() => {
      this.requireBudget();
      const now = this.now();
      if (this.issuedOtp !== undefined && now < this.issuedOtp.resendAvailableAtInMilliseconds) {
        const waitInMilliseconds = this.issuedOtp.resendAvailableAtInMilliseconds - now;
        throw problem(429, 'RATE_LIMITED', Math.ceil(waitInMilliseconds / MILLISECONDS_PER_SECOND));
      }
      this.issuedOtp = {
        expiresAtInMilliseconds: now + OTP_LIFETIME_IN_MILLISECONDS,
        resendAvailableAtInMilliseconds: now + OTP_RESEND_DELAY_IN_MILLISECONDS,
        attemptsRemaining: OTP_ATTEMPT_COUNT,
      };
      return {
        phoneLastTwoDigits: '42',
        expiresAt: new Date(this.issuedOtp.expiresAtInMilliseconds).toISOString(),
        resendAvailableAt: new Date(this.issuedOtp.resendAvailableAtInMilliseconds).toISOString(),
        attemptsRemaining: OTP_ATTEMPT_COUNT,
      };
    });
  }

  // Records consent once, checking the OTP, its tries and that the figures shown still hold.
  giveConsent(submission: ConsentSubmission, idempotencyKey: string): Promise<ConsentConfirmation> {
    return settle(() => {
      this.requireBudget();
      if (this.consent !== undefined) {
        if (this.consent.idempotencyKey === idempotencyKey) return this.consent.confirmation;
        throw problem(409, 'CONSENT_ALREADY_GIVEN');
      }
      const plan = this.findQuotedPlan(submission.offerId);
      if (
        plan.monthlyInstallmentInPaise !== submission.shownMonthlyInstallmentInPaise ||
        plan.totalPayableInPaise !== submission.shownTotalPayableInPaise
      ) {
        throw problem(409, 'SHOWN_PLAN_CHANGED');
      }
      this.checkOtp(submission.otp);
      const confirmation: ConsentConfirmation = {
        consentId: 'fixture-consent-1',
        reference: FIXTURE_RECEIPT_REFERENCE,
        consentedAt: new Date(this.now()).toISOString(),
        status: 'READY_TO_PAY',
        plan: buildFixtureConsentedPlan(plan),
      };
      this.consent = { idempotencyKey, confirmation };
      return confirmation;
    });
  }

  // Gives the receipt, moving through the configured payment statuses one read at a time.
  getReceipt(): Promise<CustomerReceipt> {
    return settle(() => {
      this.requireSession();
      if (this.consent === undefined) throw problem(409, 'CONSENT_NOT_GIVEN');
      const statusIndex = Math.min(this.receiptReadCount, this.receiptStatuses.length - 1);
      this.receiptReadCount += 1;
      const { confirmation } = this.consent;
      return {
        status: this.receiptStatuses[statusIndex] ?? 'READY_TO_PAY',
        reference: confirmation.reference,
        phoneLastTwoDigits: '42',
        consentedAt: confirmation.consentedAt,
        coolingOffNoticeStatus: 'PLACEHOLDER',
        plan: confirmation.plan,
      };
    });
  }

  // Gives the sample transcription for the purpose; like the server, it never sets the budget.
  transcribeSpeech(_audio: Blob, purpose: SpeechPurpose): Promise<SpeechTranscription> {
    return settle(() => {
      this.requireSession();
      return FIXTURE_TRANSCRIPTIONS[purpose];
    });
  }

  // Gives a tiny silent WAV as the spoken explanation; any other id is not found, as on the server.
  synthesiseExplanation(explanationId: string): Promise<Blob> {
    return settle(() => {
      this.requireSession();
      if (explanationId !== FIXTURE_EXPLANATION_ID) throw problem(404, 'EXPLANATION_NOT_FOUND');
      return buildFixtureSilentWav();
    });
  }

  // Checks the own-words answer against the quoted plan's monthly figure (sample rule).
  checkTeachBack(
    offerId: string,
    answerText: string,
    language: SupportedLanguage,
  ): Promise<TeachBackOutcome> {
    return settle(() => buildFixtureTeachBack(this.findQuotedPlan(offerId), answerText, language));
  }

  // Finds a plan of the current ranking by offer id, or fails with OFFER_NOT_FOUND.
  private findQuotedPlan(offerId: string): CustomerPlanResponse {
    this.requireBudget();
    const plan = FIXTURE_PLANS_AT_DESIGN_BUDGET.plans.find(
      (candidate) => candidate.offerId === offerId,
    );
    if (plan === undefined) throw problem(404, 'OFFER_NOT_FOUND');
    return this.quotePlan(plan);
  }

  // Spends one try of the current OTP; the last wrong try spends the OTP (ADR 0022 decision 3).
  private checkOtp(otp: string): void {
    const issuedOtp = this.issuedOtp;
    if (issuedOtp === undefined) throw problem(422, 'OTP_NOT_REQUESTED');
    if (this.now() >= issuedOtp.expiresAtInMilliseconds || issuedOtp.attemptsRemaining === 0) {
      throw problem(422, 'OTP_EXPIRED');
    }
    if (otp === FIXTURE_OTP) return;
    issuedOtp.attemptsRemaining -= 1;
    if (issuedOtp.attemptsRemaining === 0) throw problem(422, 'OTP_EXPIRED');
    throw new CustomerApiError(422, 'OTP_INCORRECT', {
      hasProblemBody: true,
      attemptsRemaining: issuedOtp.attemptsRemaining,
    });
  }
}

// Builds the error a problem+json answer with this code would give.
function problem(status: number, code: string, retryAfterInSeconds?: number): CustomerApiError {
  return new CustomerApiError(status, code, { hasProblemBody: true, retryAfterInSeconds });
}

// Runs a fixture step and gives its result or failure as a promise, as a network call would.
function settle<Result>(step: () => Result): Promise<Result> {
  try {
    return Promise.resolve(step());
  } catch (error) {
    return Promise.reject(error instanceof Error ? error : new Error(String(error)));
  }
}
