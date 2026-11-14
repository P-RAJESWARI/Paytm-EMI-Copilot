import { useLanguagePreference, type SupportedLanguage } from '@emi-copilot/shared-i18n';
import { LanguageToggle } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';
import { NavLink } from 'react-router';

import { BrandMark } from '../../shared/components/BrandMark';
import { MERCHANT_PATHS } from '../merchantPaths';

export interface MerchantSidebarProps {
  /** The shop name and device label, or undefined while they load. */
  shopName: string | undefined;
  deviceLabel: string | undefined;
}

// Gives the classes of one navigation tab, highlighted when it is the current page.
function getNavigationLinkClassName({ isActive }: { isActive: boolean }): string {
  return `flex min-h-touch-target items-center gap-3 rounded-input px-3 text-body font-semibold no-underline ${
    isActive ? 'bg-overlay-on-navy-strong text-white' : 'text-border-strong'
  }`;
}

// The navy sidebar on tablets (a top bar on phones): the two shop tabs, the shop card and the
// shop-language toggle (plan Q11).
export function MerchantSidebar({ shopName, deviceLabel }: MerchantSidebarProps) {
  const { t } = useTranslation();
  const { selectedLanguage, selectLanguage } = useLanguagePreference();
  const languageOptions: { language: SupportedLanguage; label: string }[] = [
    { language: 'en', label: t('language.english') },
    { language: 'ta', label: t('language.tamil') },
  ];
  return (
    <nav
      aria-label={t('shell.navigationLabel')}
      className="flex shrink-0 flex-col gap-2 bg-navy p-3 text-white md:min-h-screen md:w-54 md:gap-1 md:px-3 md:py-5"
    >
      <p className="flex items-center gap-2 px-2 pb-2 text-lead font-bold md:pb-4">
        <BrandMark size={28} />
        {t('common.appName')}
      </p>
      <div className="flex gap-2 md:flex-col md:gap-1">
        <NavLink to={MERCHANT_PATHS.newEmiSale} className={getNavigationLinkClassName}>
          {t('shell.newEmiSale')}
        </NavLink>
        <NavLink to={MERCHANT_PATHS.salesReport} end className={getNavigationLinkClassName}>
          {t('shell.salesReport')}
        </NavLink>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 md:mt-auto md:flex-col md:items-stretch">
        <section
          aria-label={t('shell.shopCardLabel')}
          className="rounded-input bg-overlay-on-navy px-3 py-2"
        >
          <p className="text-label text-white">{shopName ?? t('shell.loadingShop')}</p>
          {deviceLabel === undefined ? null : (
            <p className="text-caption text-border-strong">{deviceLabel}</p>
          )}
        </section>
        <LanguageToggle
          accessibleLabel={t('language.groupLabel')}
          options={languageOptions}
          selectedLanguage={selectedLanguage}
          onSelectLanguage={selectLanguage}
          surface="dark"
        />
      </div>
    </nav>
  );
}
