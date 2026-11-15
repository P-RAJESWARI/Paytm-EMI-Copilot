// TEMPORARY until the customer paths are in backendApiSchema.ts (ADR 0022 decision 6).
// Hand-written from backend/openapi.customer.json (Phase 3A) plus the approved ADR 0022 changes:
// OTP attemptsRemaining, consent without productId and downPaymentInPaise, and the explanation
// endpoint. When `make openapi` covers the customer routers, replace this file's body with
// re-exports from @emi-copilot/api-client (CustomerApiPaths = paths, each schema = ApiSchemas[...])
// and fix any compile error that shows a drift. No other file declares customer wire types.

export type EmiType = 'NO_COST' | 'STANDARD';
export type ComfortBand = 'COMFORTABLE' | 'STRETCHING' | 'RISKY';
export type ComfortCheckStatus = 'COMPLETED' | 'SKIPPED';
export type PlanReasonCode =
  | 'WITHIN_BUDGET'
  | 'ABOVE_BUDGET'
  | 'NO_EXTRA_COST'
  | 'LOWEST_MONTHLY_AMOUNT'
  | 'LOWEST_EXTRA_IN_TOTAL';
export type AlternativeKind = 'DOWN_PAYMENT' | 'LONGER_TENURE' | 'CHEAPER_MODEL';
export type ReceiptStatus = 'READY_TO_PAY' | 'PAID' | 'PAYMENT_PENDING' | 'PAYMENT_NOT_COMPLETED';
export type CoolingOffNoticeStatus = 'PLACEHOLDER';
/** Layer 3 serves only the template text; Layer 4 adds the audited AI source. */
export type ExplanationSource = 'TEMPLATE';
/** Which plan figure a highlighted amount in the explanation is (ADR 0022, C7). */
export type HighlightedAmountKind = 'MONTHLY_INSTALLMENT' | 'EXTRA_IN_TOTAL';

export interface StartCustomerSessionRequest {
  qrToken: string;
}

export interface CustomerSessionResponse {
  customerSessionId: string;
  sessionToken: string;
  sessionCode: string;
  shopName: string;
  productName: string;
  priceInPaise: number;
  expiresAt: string;
}

export interface ConfirmBudgetRequest {
  monthlyBudgetInPaise: number;
  hasCustomerConfirmed: boolean;
}

export interface ConfirmedBudgetResponse {
  monthlyBudgetInPaise: number;
  hasCustomerConfirmed: boolean;
}

export interface ComfortCheckRequest {
  hasCustomerConsented: boolean;
}

export interface ComfortCheckResponse {
  status: ComfortCheckStatus;
  isSyntheticData: boolean;
  monthlyInflowInPaise: number | null;
  existingEmisInPaise: number | null;
}

export interface PlanComfortResponse {
  band: ComfortBand;
  comfortRatioInBasisPoints: number;
  planShareInBasisPoints: number;
  existingEmisShareInBasisPoints: number;
}

export interface CustomerPlanResponse {
  position: number;
  offerId: string;
  lenderLabel: string;
  emiType: EmiType;
  tenureInMonths: number;
  monthlyInstallmentInPaise: number;
  lastInstallmentInPaise: number;
  extraInTotalInPaise: number;
  totalPayableInPaise: number;
  priceInPaise: number;
  isWithinBudget: boolean;
  amountAboveBudgetInPaise: number;
  reasonCodes: PlanReasonCode[];
  comfort: PlanComfortResponse | null;
}

export interface CustomerPlansResponse {
  monthlyBudgetInPaise: number;
  hasAnyPlanWithinBudget: boolean;
  hasComfortCheck: boolean;
  plans: CustomerPlanResponse[];
}

export interface PlanAlternativesRequest {
  offerId: string;
}

export type BasePlanResponse = Omit<CustomerPlanResponse, 'position' | 'reasonCodes'>;

export interface PlanAlternativeResponse {
  kind: AlternativeKind;
  offerId: string;
  tenureInMonths: number;
  downPaymentInPaise: number;
  financedAmountInPaise: number;
  productId?: string | null;
  productName?: string | null;
  priceInPaise: number;
  monthlyInstallmentInPaise: number;
  previousMonthlyInstallmentInPaise: number;
  extraInTotalInPaise: number;
  totalPayableInPaise: number;
  isLowerMonthlyAmount: boolean;
  isWithinBudget: boolean;
  comfort: PlanComfortResponse | null;
}

export interface PlanAlternativesResponse {
  basePlan: BasePlanResponse;
  hasLowerMonthlyAlternative: boolean;
  alternatives: PlanAlternativeResponse[];
}

export interface PlanExplanationRequest {
  offerId: string;
}

export interface HighlightedAmountResponse {
  kind: HighlightedAmountKind;
  amountInPaise: number;
}

export interface PlanExplanationResponse {
  text: string;
  language: 'en' | 'ta';
  source: ExplanationSource;
  highlightedAmounts: HighlightedAmountResponse[];
}

export interface OtpChallengeResponse {
  phoneLastTwoDigits: string;
  expiresAt: string;
  resendAvailableAt: string;
  attemptsRemaining: number;
}

export interface GiveConsentRequest {
  offerId: string;
  shownMonthlyInstallmentInPaise: number;
  shownTotalPayableInPaise: number;
  otp: string;
  hasAgreedToPlan: boolean;
}

export interface ConsentedPlanResponse {
  offerId: string;
  lenderLabel: string;
  emiType: EmiType;
  tenureInMonths: number;
  regularInstallmentInPaise: number;
  lastInstallmentInPaise: number;
  extraInTotalInPaise: number;
  totalPayableInPaise: number;
  priceInPaise: number;
  productId: string;
  productName: string;
  downPaymentInPaise: number;
  financedAmountInPaise: number;
}

export interface ConsentResponse {
  consentId: string;
  reference: string;
  consentedAt: string;
  status: ReceiptStatus;
  plan: ConsentedPlanResponse;
}

export interface CustomerReceiptResponse {
  status: ReceiptStatus;
  reference: string;
  phoneLastTwoDigits: string;
  consentedAt: string;
  coolingOffNoticeStatus: CoolingOffNoticeStatus;
  plan: ConsentedPlanResponse;
}

/** RFC 7807 body; `attemptsRemaining` is the OTP_INCORRECT extension member (ADR 0022 decision 3). */
export interface CustomerProblemDetailsResponse {
  type: string;
  title: string;
  status: number;
  detail: string;
  code: string;
  correlationId?: string | null;
  attemptsRemaining?: number;
}

/** Path and header parameters in openapi-typescript's shape; absent ones are optional never. */
type OperationParameters<PathParameters, HeaderParameters> = {
  query?: never;
  cookie?: never;
} & ([PathParameters] extends [never] ? { path?: never } : { path: PathParameters }) &
  ([HeaderParameters] extends [never] ? { header?: never } : { header: HeaderParameters });

/** A JSON request body, or an optional never when the operation takes none. */
type OperationRequestBody<RequestBody> = [RequestBody] extends [never]
  ? { requestBody?: never }
  : { requestBody: { content: { 'application/json': RequestBody } } };

/** One JSON operation in openapi-typescript's shape, so openapi-fetch types it exactly. */
type JsonOperation<
  PathParameters,
  RequestBody,
  SuccessStatus extends number,
  SuccessBody,
  HeaderParameters = never,
> = {
  parameters: OperationParameters<PathParameters, HeaderParameters>;
  responses: Record<
    SuccessStatus,
    { headers: Record<string, unknown>; content: { 'application/json': SuccessBody } }
  > & {
    default: {
      headers: Record<string, unknown>;
      content: { 'application/problem+json': CustomerProblemDetailsResponse };
    };
  };
} & OperationRequestBody<RequestBody>;

/** The path parameter every endpoint after the QR exchange carries. */
interface SessionPath {
  customerSessionId: string;
}

/** A path entry with every method openapi-typescript lists; the one used replaces its never. */
interface UnusedMethods {
  parameters: { query?: never; header?: never; path?: never; cookie?: never };
  get?: never;
  put?: never;
  post?: never;
  delete?: never;
  options?: never;
  head?: never;
  patch?: never;
  trace?: never;
}

/** The customer endpoints in openapi-typescript's `paths` shape (temporary, see the file header). */
export interface CustomerApiPaths {
  '/api/v1/customer-sessions': Omit<UnusedMethods, 'post'> & {
    post: JsonOperation<never, StartCustomerSessionRequest, 201, CustomerSessionResponse>;
  };
  '/api/v1/customer-sessions/{customerSessionId}/budget': Omit<UnusedMethods, 'put'> & {
    put: JsonOperation<SessionPath, ConfirmBudgetRequest, 200, ConfirmedBudgetResponse>;
  };
  '/api/v1/customer-sessions/{customerSessionId}/comfort-check': Omit<UnusedMethods, 'post'> & {
    post: JsonOperation<SessionPath, ComfortCheckRequest, 200, ComfortCheckResponse>;
  };
  '/api/v1/customer-sessions/{customerSessionId}/plans': Omit<UnusedMethods, 'get'> & {
    get: JsonOperation<SessionPath, never, 200, CustomerPlansResponse>;
  };
  '/api/v1/customer-sessions/{customerSessionId}/alternatives': Omit<UnusedMethods, 'post'> & {
    post: JsonOperation<SessionPath, PlanAlternativesRequest, 200, PlanAlternativesResponse>;
  };
  '/api/v1/customer-sessions/{customerSessionId}/explanation': Omit<UnusedMethods, 'post'> & {
    post: JsonOperation<SessionPath, PlanExplanationRequest, 200, PlanExplanationResponse>;
  };
  '/api/v1/customer-sessions/{customerSessionId}/consent/otp': Omit<UnusedMethods, 'post'> & {
    post: JsonOperation<SessionPath, never, 200, OtpChallengeResponse>;
  };
  '/api/v1/customer-sessions/{customerSessionId}/consent': Omit<UnusedMethods, 'post'> & {
    post: JsonOperation<
      SessionPath,
      GiveConsentRequest,
      201,
      ConsentResponse,
      { 'Idempotency-Key': string }
    >;
  };
  '/api/v1/customer-sessions/{customerSessionId}/receipt': Omit<UnusedMethods, 'get'> & {
    get: JsonOperation<SessionPath, never, 200, CustomerReceiptResponse>;
  };
}
