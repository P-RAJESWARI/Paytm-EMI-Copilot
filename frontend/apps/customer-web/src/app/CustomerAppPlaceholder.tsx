import { useLanguagePreference, type SupportedLanguage } from '@emi-copilot/shared-i18n';
import { LanguageToggle } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

// The customer app's only screen until Layer 3: the app name, one line and the language toggle.
export function CustomerAppPlaceholder() {
  const { t } = useTranslation();
  const { selectedLanguage, selectLanguage } = useLanguagePreference();
  const languageOptions: { language: SupportedLanguage; label: string }[] = [
    { language: 'en', label: t('language.english') },
    { language: 'ta', label: t('language.tamil') },
  ];
  return (
    <main className="flex min-h-screen flex-col gap-4 bg-light-blue p-4">
      <LanguageToggle
        accessibleLabel={t('language.groupLabel')}
        options={languageOptions}
        selectedLanguage={selectedLanguage}
        onSelectLanguage={selectLanguage}
      />
      <h1 className="text-title text-navy">{t('common.appName')}</h1>
      <p className="text-body">{t('placeholder.tagline')}</p>
    </main>
  );
}
