import type { SupportedLanguage } from '@emi-copilot/shared-i18n';

import { createCustomerApiClient, type CustomerApiClient } from './createCustomerApiClient';
import { CUSTOMER_SESSION_TOKEN_INVALID_CODE, CustomerApiError } from './customerApiError';
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
} from './CustomerFlowApi';
import { readApiData } from './readApiData';

/** The one session this phone holds, in memory only (never browser storage; ADR 0022 decision 4). */
interface ActiveSession {
  customerSessionId: string;
  sessionToken: string;
}

/** The path parameters of every call after the QR exchange. */
interface SessionPathParameters {
  path: { customerSessionId: string };
}

export interface HttpCustomerFlowApiOptions {
  baseUrl: string;
  fetchFunction: (request: Request) => Promise<Response>;
}

// Pattern: Adapter. Implements CustomerFlowApi over the customer REST endpoints with openapi-fetch;
// it keeps the session token in memory and adds it to every call through the client middleware.
export class HttpCustomerFlowApi implements CustomerFlowApi {
  private activeSession: ActiveSession | undefined;
  private readonly apiClient: CustomerApiClient;

  // Builds the customer client whose middleware reads this instance's in-memory session token.
  constructor({ baseUrl, fetchFunction }: HttpCustomerFlowApiOptions) {
    this.apiClient = createCustomerApiClient({
      baseUrl,
      fetchFunction,
      getSessionToken: () => this.activeSession?.sessionToken,
    });
  }

  // Runs a call with the active session's path parameters, or rejects as a lost session without
  // sending anything when no session is open.
  private callInSession<Data>(
    call: (sessionPath: SessionPathParameters) => Promise<Data>,
  ): Promise<Data> {
    if (this.activeSession === undefined) {
      return Promise.reject(new CustomerApiError(401, CUSTOMER_SESSION_TOKEN_INVALID_CODE));
    }
    return call({ path: { customerSessionId: this.activeSession.customerSessionId } });
  }

  // Exchanges the QR token once and keeps the session token here; screens get the rest.
  async startSession(qrToken: string): Promise<CustomerSession> {
    const response = await readApiData(
      this.apiClient.POST('/api/v1/customer-sessions', { body: { qrToken } }),
    );
    const { sessionToken, ...session } = response;
    this.activeSession = { customerSessionId: session.customerSessionId, sessionToken };
    return session;
  }

  // Records the monthly budget the customer confirmed on C2.
  async confirmBudget(monthlyBudgetInPaise: number): Promise<void> {
    await this.callInSession((params) =>
      readApiData(
        this.apiClient.PUT('/api/v1/customer-sessions/{customerSessionId}/budget', {
          params,
          body: { monthlyBudgetInPaise, hasCustomerConfirmed: true },
        }),
      ),
    );
  }

  // Runs the consented comfort check, or records that the customer skipped it (C3).
  answerComfortCheck(hasCustomerConsented: boolean): Promise<ComfortCheckResult> {
    return this.callInSession((params) =>
      readApiData(
        this.apiClient.POST('/api/v1/customer-sessions/{customerSessionId}/comfort-check', {
          params,
          body: { hasCustomerConsented },
        }),
      ),
    );
  }

  // Lists every plan for the confirmed budget in the server's order (C4).
  listPlans(): Promise<PlanComparison> {
    return this.callInSession((params) =>
      readApiData(
        this.apiClient.GET('/api/v1/customer-sessions/{customerSessionId}/plans', {
          params,
        }),
      ),
    );
  }

  // Asks the engine for smarter alternatives to one plan (C6).
  findAlternatives(offerId: string): Promise<PlanAlternatives> {
    return this.callInSession((params) =>
      readApiData(
        this.apiClient.POST('/api/v1/customer-sessions/{customerSessionId}/alternatives', {
          params,
          body: { offerId },
        }),
      ),
    );
  }

  // Gets the plain-language explanation of one plan in the customer's language (C7).
  explainPlan(offerId: string, language: SupportedLanguage): Promise<PlanExplanation> {
    return this.callInSession((params) =>
      readApiData(
        this.apiClient.POST('/api/v1/customer-sessions/{customerSessionId}/explanation', {
          params,
          body: { offerId },
          headers: { 'Accept-Language': language },
        }),
      ),
    );
  }

  // Sends (or re-sends) the consent OTP to the phone the payment side knows (C9).
  requestConsentOtp(): Promise<OtpChallenge> {
    return this.callInSession((params) =>
      readApiData(
        this.apiClient.POST('/api/v1/customer-sessions/{customerSessionId}/consent/otp', {
          params,
        }),
      ),
    );
  }

  // Records consent to the exact plan C9 showed; the same key replays a retry safely.
  giveConsent(submission: ConsentSubmission, idempotencyKey: string): Promise<ConsentConfirmation> {
    return this.callInSession((params) =>
      readApiData(
        this.apiClient.POST('/api/v1/customer-sessions/{customerSessionId}/consent', {
          params: { ...params, header: { 'Idempotency-Key': idempotencyKey } },
          body: { ...submission, hasAgreedToPlan: true },
        }),
      ),
    );
  }

  // Reads the receipt and the payment status the shop's side has reached (C10).
  getReceipt(): Promise<CustomerReceipt> {
    return this.callInSession((params) =>
      readApiData(
        this.apiClient.GET('/api/v1/customer-sessions/{customerSessionId}/receipt', {
          params,
        }),
      ),
    );
  }
}
