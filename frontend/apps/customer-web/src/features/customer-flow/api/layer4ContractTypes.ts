// TEMPORARY (Layer 4): hand-written wire types for the speech, synthesis and teach-back endpoints
// and the session's isVoiceAvailable flag, until the backend runs `make openapi` and the generated
// api-client has them. Then this file is replaced by names in customerContractTypes.ts. (The
// explanation's explanationId and AI_AUDITED source already come from the generated client.)
import type { CustomerSessionResponse, PlanExplanationResponse } from './customerContractTypes';

/** What a recording is for; the server parses an amount only for BUDGET. */
export type SpeechPurpose = 'BUDGET' | 'TEACH_BACK';

/** POST .../speech/transcriptions answer; it never changes the budget. */
export interface SpeechTranscriptionResponse {
  transcript: string;
  recognisedAmountInPaise: number | null;
  isLikelyMisheard: boolean;
}

/** POST .../teach-back outcome; advisory only, the customer may always continue. */
export type TeachBackResult = 'CLOSE_ENOUGH' | 'TRY_AGAIN';

/** One plan figure the teach-back answer highlights (same shape as the explanation's). */
export type TeachBackHighlightedAmount = PlanExplanationResponse['highlightedAmounts'][number];

/** POST .../teach-back answer, in the customer's language. */
export interface TeachBackResponse {
  result: TeachBackResult;
  title: string;
  body: string;
  heardText: string | null;
  highlightedAmounts: TeachBackHighlightedAmount[];
}

/** The session with the Layer 4 flag saying whether speech is switched on for this phone. */
export type Layer4CustomerSessionResponse = CustomerSessionResponse & {
  isVoiceAvailable: boolean;
};

// Reads the Layer 4 session flag from whatever the server sent; an older server means no voice.
export function readLayer4Session(
  response: CustomerSessionResponse,
): Layer4CustomerSessionResponse {
  const sessionFields: Partial<Record<'isVoiceAvailable', unknown>> = response;
  return { ...response, isVoiceAvailable: sessionFields.isVoiceAvailable === true };
}
