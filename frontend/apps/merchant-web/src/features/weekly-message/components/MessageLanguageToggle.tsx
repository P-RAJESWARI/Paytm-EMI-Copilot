import type { SupportedLanguage } from '@emi-copilot/shared-i18n';
import { LanguageToggle, type LanguageToggleSurface } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

export interface MessageLanguageToggleProps {
  messageLanguage: SupportedLanguage;
  onSelectMessageLanguage: (language: SupportedLanguage) => void;
  surface: LanguageToggleSurface;
}

// The EN / தமிழ் switch for the message only; its group name is in the shop language.
export function MessageLanguageToggle({
  messageLanguage,
  onSelectMessageLanguage,
  surface,
}: MessageLanguageToggleProps) {
  const { t } = useTranslation();
  return (
    <LanguageToggle
      accessibleLabel={t('weeklyMessage.languageLabel')}
      options={[
        { language: 'en', label: t('language.english') },
        { language: 'ta', label: t('language.tamil') },
      ]}
      selectedLanguage={messageLanguage}
      onSelectLanguage={onSelectMessageLanguage}
      surface={surface}
    />
  );
}
