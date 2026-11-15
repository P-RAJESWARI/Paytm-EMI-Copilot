import { useLanguagePreference } from '@emi-copilot/shared-i18n';
import { useMutation } from '@tanstack/react-query';

import { useCustomerFlowApi, type SpeechPurpose } from '../../customer-flow';

// Sends one recording to speech-to-text for a purpose (BUDGET or TEACH_BACK), listening in the
// customer's chosen language; the answer only fills a field, and the customer still confirms it.
export function useSpeechTranscription(purpose: SpeechPurpose) {
  const customerFlowApi = useCustomerFlowApi();
  const { selectedLanguage } = useLanguagePreference();
  return useMutation({
    mutationFn: (audio: Blob) => customerFlowApi.transcribeSpeech(audio, purpose, selectedLanguage),
  });
}
