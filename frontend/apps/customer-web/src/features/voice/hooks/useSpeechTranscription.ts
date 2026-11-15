import { useMutation } from '@tanstack/react-query';

import { useCustomerFlowApi, type SpeechPurpose } from '../../customer-flow';

// Sends one recording to speech-to-text for a purpose (BUDGET or TEACH_BACK); the answer only
// fills a field on screen, and the customer still confirms it by tapping.
export function useSpeechTranscription(purpose: SpeechPurpose) {
  const customerFlowApi = useCustomerFlowApi();
  return useMutation({
    mutationFn: (audio: Blob) => customerFlowApi.transcribeSpeech(audio, purpose),
  });
}
