import type { SupportedLanguage } from '@emi-copilot/shared-i18n';

import type {
  ComfortCheckResponse,
  ConsentResponse,
  CustomerPlanResponse,
  CustomerPlansResponse,
  CustomerReceiptResponse,
  CustomerSessionResponse,
  OtpChallengeResponse,
  PlanAlternativeResponse,
  PlanAlternativesResponse,
  PlanExplanationResponse,
  SpeechTranscriptionPurpose,
  SpeechTranscriptionResponse,
  TeachBackResponse,
} from './customerContractTypes';

/** The session as screens see it: the shop, the item and the code; the token never leaves the API. */
export type CustomerSession = Omit<CustomerSessionResponse, 'sessionToken'>;
/** The comfort check outcome: completed with synthetic inflow and EMIs, or skipped. */
export type ComfortCheckResult = ComfortCheckResponse;
/** Every plan for the confirmed budget, ranked by the server; none is ever hidden. */
export type PlanComparison = CustomerPlansResponse;
/** One plan exactly as the server quoted it; the UI shows these figures and never works them out. */
export type CustomerPlan = CustomerPlanResponse;
export type PlanAlternatives = PlanAlternativesResponse;
export type PlanAlternative = PlanAlternativeResponse;
export type PlanExplanation = PlanExplanationResponse;
export type SpeechTranscription = SpeechTranscriptionResponse;
export type TeachBackOutcome = TeachBackResponse;
export type SpeechPurpose = SpeechTranscriptionPurpose;
export type OtpChallenge = OtpChallengeResponse;
export type ConsentConfirmation = ConsentResponse;
export type CustomerReceipt = CustomerReceiptResponse;

/** What the customer agrees to on C9: the offer and the exact figures C9 showed, plus the OTP. */
export interface ConsentSubmission {
  offerId: string;
  shownMonthlyInstallmentInPaise: number;
  shownTotalPayableInPaise: number;
  otp: string;
}

// Pattern: Port (UI side of Adapter plus Factory). The customer flow's server calls in UI terms,
// so screens work the same against the fixture and the real API (PARALLEL_LAYER_3.md section 3).
// Every call after startSession is bound to that one session; a lost session rejects with
// CUSTOMER_SESSION_TOKEN_INVALID.
export interface CustomerFlowApi {
  /** Trades the single-use QR token for a session; the session token stays inside the API. */
  startSession: (qrToken: string) => Promise<CustomerSession>;
  confirmBudget: (monthlyBudgetInPaise: number) => Promise<void>;
  answerComfortCheck: (hasCustomerConsented: boolean) => Promise<ComfortCheckResult>;
  listPlans: () => Promise<PlanComparison>;
  findAlternatives: (offerId: string) => Promise<PlanAlternatives>;
  explainPlan: (offerId: string, language: SupportedLanguage) => Promise<PlanExplanation>;
  requestConsentOtp: () => Promise<OtpChallenge>;
  /** Consent is recorded in the customer's language, which the server keeps for the receipt. */
  giveConsent: (
    submission: ConsentSubmission,
    idempotencyKey: string,
    language: SupportedLanguage,
  ) => Promise<ConsentConfirmation>;
  getReceipt: () => Promise<CustomerReceipt>;
  /** Turns one short recording, spoken in the language given, into text (and an amount for
   * BUDGET); it never sets the budget. */
  transcribeSpeech: (
    audio: Blob,
    purpose: SpeechPurpose,
    language: SupportedLanguage,
  ) => Promise<SpeechTranscription>;
  /** Reads an explanation aloud; the answer is the audio itself. */
  synthesiseExplanation: (explanationId: string) => Promise<Blob>;
  /** Checks the customer's own-words answer against the plan; advice only, never a gate. */
  checkTeachBack: (
    offerId: string,
    answerText: string,
    language: SupportedLanguage,
  ) => Promise<TeachBackOutcome>;
}
