import { useLanguagePreference, type SupportedLanguage } from '@emi-copilot/shared-i18n';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

// The weekly message's own EN / தமிழ் switch (plan Q11): it starts in the shop language and
// changes only the message, with a translator fixed to that language for the message's labels.
export function useMessageLanguage() {
  const { selectedLanguage } = useLanguagePreference();
  const [messageLanguage, setMessageLanguage] = useState<SupportedLanguage>(selectedLanguage);
  const { t: translateInMessageLanguage } = useTranslation(undefined, { lng: messageLanguage });
  return { messageLanguage, setMessageLanguage, translateInMessageLanguage };
}
