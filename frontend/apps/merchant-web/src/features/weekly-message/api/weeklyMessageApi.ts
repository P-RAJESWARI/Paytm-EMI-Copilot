import type { ApiSchemas, BackendApiClient } from '@emi-copilot/api-client';

import { readApiData } from '../../../shared/api/readApiData';

export type WeeklyMessage = ApiSchemas['WeeklyMessageResponse'];
/** One language's text of the week's message. */
export type WeeklyMessageText = WeeklyMessage['messages']['en'];

// True when this language's text was written by the AI and passed the number audit.
export function isWrittenByAi(messageText: WeeklyMessageText): boolean {
  return messageText.source === 'AI_AUDITED';
}

/** The current week's message (GET /reports/weekly-message without a period). */
export const WEEKLY_MESSAGE_QUERY_KEY = ['report', 'weekly-message'] as const;

// Reads this week's message in English and Tamil, written by the backend (template or audited AI).
export function fetchWeeklyMessage(apiClient: BackendApiClient): Promise<WeeklyMessage> {
  return readApiData(apiClient.GET('/api/v1/reports/weekly-message', {}));
}

// Marks the week's message sent to the shop's phone through the labelled Mock delivery.
export function sendWeeklyMessage(
  apiClient: BackendApiClient,
  periodStartDate: string,
): Promise<WeeklyMessage> {
  return readApiData(
    apiClient.POST('/api/v1/reports/weekly-message/send', { body: { periodStartDate } }),
  );
}
