import { createBackendApiClient, type BackendApiClient } from '@emi-copilot/api-client';
import type { SupportedLanguage } from '@emi-copilot/shared-i18n';

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
  SpeechPurpose,
  SpeechTranscription,
  TeachBackOutcome,
} from './CustomerFlowApi';
import { readApiData } from './readApiData';
import { sendSessionRequest, type SessionRequest } from './sendSessionRequest';

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

// Pattern: Adapter. Implements CustomerFlowApi over the customer REST endpoints with the generated
// api-client; it keeps the session token in memory and adds it to every call through the client's
// session-token middleware.
export class HttpCustomerFlowApi implements CustomerFlowApi {
  private activeSession: ActiveSession | undefined;
  private readonly apiClient: BackendApiClient;
  private readonly baseUrl: string;
  private readonly fetchFunction: (request: Request) => Promise<Response>;

  // Builds the generated client whose middleware reads this instance's in-memory session token.
  constructor({ baseUrl, fetchFunction }: HttpCustomerFlowApiOptions) {
    this.baseUrl = baseUrl;
    this.fetchFunction = fetchFunction;
    this.apiClient = createBackendApiClient({
      baseUrl,
      fetch: fetchFunction,
      getCustomerSessionToken: () => this.activeSession?.sessionToken,
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

  // Records consent to the exact plan C9 showed, in the customer's language (Accept-Language);
  // the same key replays a retry safely.
  giveConsent(
    submission: ConsentSubmission,
    idempotencyKey: string,
    language: SupportedLanguage,
  ): Promise<ConsentConfirmation> {
    return this.callInSession((params) =>
      readApiData(
        this.apiClient.POST('/api/v1/customer-sessions/{customerSessionId}/consent', {
          params: { ...params, header: { 'Idempotency-Key': idempotencyKey } },
          body: { ...submission, hasAgreedToPlan: true },
          headers: { 'Accept-Language': language },
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

  // Sends one raw recording as the request body with its own content type and the language to
  // listen for (C2 and C8 microphone).
  async transcribeSpeech(
    audio: Blob,
    purpose: SpeechPurpose,
    language: SupportedLanguage,
  ): Promise<SpeechTranscription> {
    const response = await this.sendInSession('/speech/transcriptions', {
      body: await audio.arrayBuffer(),
      contentType: audio.type === '' ? 'audio/webm' : audio.type,
      query: `?purpose=${purpose}`,
      language,
    });
    return (await response.json()) as SpeechTranscription;
  }

  // Fetches the spoken explanation as audio bytes (C7 Listen).
  synthesiseExplanation(explanationId: string): Promise<Blob> {
    return this.callInSession((params) =>
      readApiData(
        this.apiClient.POST('/api/v1/customer-sessions/{customerSessionId}/speech/synthesis', {
          params,
          body: { explanationId },
          parseAs: 'blob',
        }),
      ),
    );
  }

  // Sends the customer's own-words answer for the plan in their language (C8).
  checkTeachBack(
    offerId: string,
    answerText: string,
    language: SupportedLanguage,
  ): Promise<TeachBackOutcome> {
    return this.callInSession((params) =>
      readApiData(
        this.apiClient.POST('/api/v1/customer-sessions/{customerSessionId}/teach-back', {
          params,
          body: { offerId, answerText },
          headers: { 'Accept-Language': language },
        }),
      ),
    );
  }

  // Sends a raw-body call under the active session's path. The generated schema types the raw
  // audio body as a string, so only transcription uses this instead of the typed client.
  private sendInSession(
    pathAfterSession: string,
    options: Pick<SessionRequest, 'body' | 'contentType' | 'language'> & { query: string },
  ): Promise<Response> {
    const activeSession = this.activeSession;
    if (activeSession === undefined) {
      return Promise.reject(new CustomerApiError(401, CUSTOMER_SESSION_TOKEN_INVALID_CODE));
    }
    const sessionPath = `/api/v1/customer-sessions/${encodeURIComponent(activeSession.customerSessionId)}`;
    return sendSessionRequest({
      baseUrl: this.baseUrl,
      fetchFunction: this.fetchFunction,
      sessionToken: activeSession.sessionToken,
      path: `${sessionPath}${pathAfterSession}${options.query}`,
      body: options.body,
      contentType: options.contentType,
      language: options.language,
    });
  }
}
