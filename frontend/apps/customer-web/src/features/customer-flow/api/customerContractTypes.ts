// The customer wire types, named once from the generated api-client (backend/openapi.json, ADR
// 0022 decision 6). No other file declares customer wire types; `make openapi` keeps them current.
import type { ApiSchemas } from '@emi-copilot/api-client';

export type EmiType = ApiSchemas['EmiType'];
export type ComfortBand = ApiSchemas['ComfortBand'];
export type ComfortCheckStatus = ApiSchemas['ComfortCheckStatus'];
export type PlanReasonCode = ApiSchemas['PlanReasonCode'];
export type AlternativeKind = ApiSchemas['AlternativeKind'];
export type ReceiptStatus = ApiSchemas['ReceiptStatus'];
export type CoolingOffNoticeStatus = ApiSchemas['CoolingOffNoticeStatus'];
/** AI_AUDITED text passed the number audit; TEMPLATE is the standard text (Layer 4). */
export type ExplanationSource = ApiSchemas['ExplanationSource'];
/** Which plan figure a highlighted amount in the explanation is (ADR 0022, C7). */
export type HighlightedAmountKind = ApiSchemas['HighlightedAmountKind'];

export type CustomerSessionResponse = ApiSchemas['CustomerSessionResponse'];
export type ComfortCheckResponse = ApiSchemas['ComfortCheckResponse'];
export type PlanComfortResponse = ApiSchemas['PlanComfortResponse'];
export type CustomerPlanResponse = ApiSchemas['CustomerPlanResponse'];
export type CustomerPlansResponse = ApiSchemas['CustomerPlansResponse'];
export type BasePlanResponse = ApiSchemas['BasePlanResponse'];
export type PlanAlternativeResponse = ApiSchemas['PlanAlternativeResponse'];
export type PlanAlternativesResponse = ApiSchemas['PlanAlternativesResponse'];
export type HighlightedAmountResponse = ApiSchemas['HighlightedAmountResponse'];
export type PlanExplanationResponse = ApiSchemas['PlanExplanationResponse'];
export type OtpChallengeResponse = ApiSchemas['OtpChallengeResponse'];
export type GiveConsentRequest = ApiSchemas['GiveConsentRequest'];
export type ConsentedPlanResponse = ApiSchemas['ConsentedPlanResponse'];
export type ConsentResponse = ApiSchemas['ConsentResponse'];
export type CustomerReceiptResponse = ApiSchemas['CustomerReceiptResponse'];
/** RFC 7807 body; `attemptsRemaining` is the OTP_INCORRECT extension member (ADR 0022 decision 3). */
export type CustomerProblemDetailsResponse = ApiSchemas['CustomerProblemDetailsResponse'];
