import type { SupportedLanguage } from '@emi-copilot/shared-i18n';
import { Button } from '@emi-copilot/ui-kit';
import type { TFunction } from 'i18next';
import { useId, type ReactNode } from 'react';
import { Link } from 'react-router';

import { MERCHANT_PATHS } from '../../../app/merchantPaths';
import { isWrittenByAi, type WeeklyMessage } from '../api/weeklyMessageApi';
import { MessageLanguageToggle } from './MessageLanguageToggle';

export interface WeeklySummaryCardProps {
  weeklyMessage: WeeklyMessage | undefined;
  /** Shown instead of the message while it loads or after an error. */
  placeholder?: ReactNode;
  messageLanguage: SupportedLanguage;
  onSelectMessageLanguage: (language: SupportedLanguage) => void;
  translateInMessageLanguage: TFunction;
  onSendToPhone: () => void;
  isSending: boolean;
  /** Translated, calm message when sending failed. */
  sendProblemMessage?: string | undefined;
}

// M5's navy "This week in short" card: the backend's message in the chosen language, "Send to
// my phone" (or "Sent to your phone") and a link to the phone view (M8). AI-written text carries
// a small note; there is no audio on the merchant side.
export function WeeklySummaryCard(props: WeeklySummaryCardProps) {
  const { weeklyMessage, messageLanguage, translateInMessageLanguage: t } = props;
  const headingId = useId();
  const messageText = weeklyMessage?.messages[messageLanguage];
  return (
    <section
      aria-labelledby={headingId}
      lang={messageLanguage}
      className="flex flex-col gap-3 rounded-card bg-navy p-6 text-white"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id={headingId} className="text-title">
          {t('weeklyMessage.summaryHeading')}
        </h2>
        <MessageLanguageToggle
          messageLanguage={messageLanguage}
          onSelectMessageLanguage={props.onSelectMessageLanguage}
          surface="dark"
        />
      </div>
      {props.placeholder}
      {messageText === undefined ? null : (
        <div className="flex flex-col gap-2">
          <p className="text-body font-bold text-cyan-soft">{messageText.title}</p>
          {messageText.paragraphs.map((paragraph) => (
            <p key={paragraph} className="text-body">
              {paragraph}
            </p>
          ))}
          {isWrittenByAi(messageText) ? (
            <p className="text-caption text-cyan-soft">{t('weeklyMessage.writtenByAi')}</p>
          ) : null}
        </div>
      )}
      {weeklyMessage === undefined ? null : (
        <div className="flex flex-wrap items-center gap-4">
          {weeklyMessage.isSent ? (
            <p role="status" className="text-body font-semibold text-white">
              {t('weeklyMessage.sentToPhone')}
            </p>
          ) : (
            <Button onClick={props.onSendToPhone} disabled={props.isSending}>
              {props.isSending ? t('weeklyMessage.sending') : t('weeklyMessage.sendToPhone')}
            </Button>
          )}
          <Link
            to={MERCHANT_PATHS.weeklyMessage}
            className="min-h-touch-target content-center text-body font-semibold text-cyan-soft underline"
          >
            {t('weeklyMessage.openPhoneView')}
          </Link>
        </div>
      )}
      {props.sendProblemMessage === undefined ? null : (
        <p role="alert" className="text-body text-white">
          {props.sendProblemMessage}
        </p>
      )}
    </section>
  );
}
