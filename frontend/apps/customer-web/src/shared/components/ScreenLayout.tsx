import { useLanguagePreference, type SupportedLanguage } from '@emi-copilot/shared-i18n';
import { LanguageToggle } from '@emi-copilot/ui-kit';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { BrandMark } from './BrandMark';

export interface ScreenLayoutProps {
  /** The screen content under the header. */
  children: ReactNode;
  /** The action area pinned to the bottom of the screen, such as Continue. */
  footer?: ReactNode;
  /** Shows a back button that calls this; screens without one show the app name instead. */
  onBack?: (() => void) | undefined;
  /** Translated position, for example "Step 1 of 4"; shown between back and the language toggle. */
  stepLabel?: string | undefined;
}

// The frame of every customer screen (phone first): back or app name, the step, the EN / தமிழ்
// toggle on every screen (frontend.md section 7), the content, and a bottom action area.
export function ScreenLayout({ children, footer, onBack, stepLabel }: ScreenLayoutProps) {
  const { t } = useTranslation();
  const { selectedLanguage, selectLanguage } = useLanguagePreference();
  const languageOptions: { language: SupportedLanguage; label: string }[] = [
    { language: 'en', label: t('language.english') },
    { language: 'ta', label: t('language.tamil') },
  ];
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-light-blue">
      <header className="flex items-center justify-between gap-2 border-b border-border bg-white px-3 py-2">
        {onBack === undefined ? (
          <div className="flex items-center gap-2 pl-1 text-body font-bold text-navy">
            <BrandMark />
            {t('common.appName')}
          </div>
        ) : (
          <button
            type="button"
            onClick={onBack}
            aria-label={t('common.back')}
            className="flex min-h-touch-target min-w-touch-target items-center justify-center rounded-input text-navy"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M15 5l-7 7 7 7" />
            </svg>
          </button>
        )}
        {stepLabel === undefined ? null : <p className="text-label text-slate">{stepLabel}</p>}
        <LanguageToggle
          accessibleLabel={t('language.groupLabel')}
          options={languageOptions}
          selectedLanguage={selectedLanguage}
          onSelectLanguage={selectLanguage}
        />
      </header>
      <main className="flex flex-1 flex-col gap-5 px-4 py-6 text-body">{children}</main>
      {footer === undefined ? null : (
        <div className="sticky bottom-0 flex flex-col gap-3 border-t border-border bg-white p-4">
          {footer}
        </div>
      )}
    </div>
  );
}
