import { useLanguagePreference, type SupportedLanguage } from '@emi-copilot/shared-i18n';
import { Card, LanguageToggle } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

// The merchant shell until step 2.6: the brand panel copy and the shop-language toggle.
export function AppShellPlaceholderPage() {
  const { t } = useTranslation();
  const { selectedLanguage, selectLanguage } = useLanguagePreference();
  const languageOptions: { language: SupportedLanguage; label: string }[] = [
    { language: 'en', label: t('language.english') },
    { language: 'ta', label: t('language.tamil') },
  ];
  return (
    <main className="flex min-h-screen items-center justify-center bg-light-blue p-8">
      <Card surface="navy" padding="roomy" className="flex max-w-xl flex-col gap-4">
        <h1 className="text-heading">{t('common.appName')}</h1>
        <p className="text-title">{t('brandPanel.tagline')}</p>
        <p className="text-body text-border-strong">{t('brandPanel.description')}</p>
        <p className="text-label font-normal text-border-strong">{t('brandPanel.audience')}</p>
        <LanguageToggle
          accessibleLabel={t('language.groupLabel')}
          options={languageOptions}
          selectedLanguage={selectedLanguage}
          onSelectLanguage={selectLanguage}
          surface="dark"
        />
      </Card>
    </main>
  );
}
