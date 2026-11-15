import type { SupportedLanguage } from '@emi-copilot/shared-i18n';
import { getButtonClassName } from '@emi-copilot/ui-kit';
import type { TFunction } from 'i18next';
import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { MERCHANT_PATHS } from '../../../app/merchantPaths';
import { BrandMark } from '../../../shared/components/BrandMark';
import {
  formatShopTime,
  formatShopWeekdayAndDate,
} from '../../../shared/formatting/formatShopTime';
import { isWrittenByAi, type WeeklyMessage } from '../api/weeklyMessageApi';
import { MessageLanguageToggle } from './MessageLanguageToggle';

export interface WeeklyMessagePhoneViewProps {
  weeklyMessage: WeeklyMessage | undefined;
  /** Shown instead of the message while it loads or after an error. */
  placeholder?: ReactNode;
  messageLanguage: SupportedLanguage;
  onSelectMessageLanguage: (language: SupportedLanguage) => void;
  translateInMessageLanguage: TFunction;
}

// M8: the weekly message as it reads on the shop owner's phone, chat style, in the chosen
// language, with the time it was sent and a way to the full report. AI-written text carries a
// small note; there is no audio on the merchant side.
export function WeeklyMessagePhoneView(props: WeeklyMessagePhoneViewProps) {
  const { weeklyMessage, messageLanguage, translateInMessageLanguage: t } = props;
  const messageText = weeklyMessage?.messages[messageLanguage];
  const sentAt = weeklyMessage?.sentAt ?? null;
  return (
    <div
      lang={messageLanguage}
      className="mx-auto flex min-h-screen w-full max-w-100 flex-col bg-message-background"
    >
      <header className="flex items-center justify-between gap-3 bg-white px-4 py-3">
        <div className="flex items-center gap-3 text-navy">
          <span className="rounded-input bg-navy p-1">
            <BrandMark size={28} />
          </span>
          <div className="flex flex-col">
            <h1 className="text-body font-bold">{t('common.appName')}</h1>
            <p className="text-caption text-slate">{t('weeklyMessage.subtitle')}</p>
          </div>
        </div>
        <MessageLanguageToggle
          messageLanguage={messageLanguage}
          onSelectMessageLanguage={props.onSelectMessageLanguage}
          surface="light"
        />
      </header>
      <main className="flex flex-1 flex-col gap-4 p-4">
        {props.placeholder}
        {sentAt === null ? null : (
          <p className="self-center rounded-pill bg-white px-3 py-1 text-caption text-slate">
            {formatShopWeekdayAndDate(sentAt, messageLanguage)}
          </p>
        )}
        {messageText === undefined ? null : (
          <article className="flex flex-col gap-2 rounded-card bg-white p-4 text-deep-navy shadow-card">
            <h2 className="text-body font-bold text-navy">{messageText.title}</h2>
            {messageText.paragraphs.map((paragraph) => (
              <p key={paragraph} className="text-body">
                {paragraph}
              </p>
            ))}
            {isWrittenByAi(messageText) ? (
              <p className="text-caption text-slate">{t('weeklyMessage.writtenByAi')}</p>
            ) : null}
            <p className="self-end text-caption text-slate">
              {sentAt === null
                ? t('weeklyMessage.notSentYet')
                : formatShopTime(sentAt, messageLanguage)}
            </p>
          </article>
        )}
        <Link
          to={MERCHANT_PATHS.salesReport}
          className={getButtonClassName({ size: 'large', isFullWidth: true })}
        >
          {t('weeklyMessage.openSalesReport')}
        </Link>
      </main>
    </div>
  );
}
