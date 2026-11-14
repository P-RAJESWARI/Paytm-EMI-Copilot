import { useLanguagePreference, type SupportedLanguage } from '@emi-copilot/shared-i18n';
import { LanguageToggle } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import { BrandMark } from '../../../shared/components/BrandMark';

// The navy M1 panel: product name, tagline and the shop-language toggle (before pairing too).
export function BrandPanel() {
  const { t } = useTranslation();
  const { selectedLanguage, selectLanguage } = useLanguagePreference();
  const languageOptions: { language: SupportedLanguage; label: string }[] = [
    { language: 'en', label: t('language.english') },
    { language: 'ta', label: t('language.tamil') },
  ];
  return (
    <section className="flex shrink-0 flex-col justify-between gap-6 bg-navy p-6 text-white md:w-105 md:p-12">
      <p className="flex items-center gap-3 text-title">
        <BrandMark size={36} />
        {t('common.appName')}
      </p>
      <div className="flex flex-col gap-4">
        <p className="text-heading">{t('brandPanel.tagline')}</p>
        <p className="text-body text-border-strong">{t('brandPanel.description')}</p>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <p className="text-label font-normal text-border-strong">{t('brandPanel.audience')}</p>
        <LanguageToggle
          accessibleLabel={t('language.groupLabel')}
          options={languageOptions}
          selectedLanguage={selectedLanguage}
          onSelectLanguage={selectLanguage}
          surface="dark"
        />
      </div>
    </section>
  );
}
