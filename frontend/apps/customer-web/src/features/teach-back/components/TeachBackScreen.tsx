import { Button } from '@emi-copilot/ui-kit';
import { useId, type FormEvent, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import type { CustomerPlan, TeachBackOutcome } from '../../customer-flow';
import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { ScreenTitle } from '../../../shared/components/ScreenTitle';
import { getPlanNameKey } from '../../../shared/plan/planWording';
import { TeachBackResultCard } from './TeachBackResultCard';

/** The server accepts answers of 1 to 500 characters. */
export const MAXIMUM_ANSWER_LENGTH = 500;

export interface TeachBackScreenProps {
  plan: CustomerPlan;
  answerText: string;
  onChangeAnswerText: (answerText: string) => void;
  /** The microphone row when voice is on; undefined hides it. */
  voiceSection?: ReactNode;
  isChecking: boolean;
  outcome: TeachBackOutcome | undefined;
  hasCheckFailed: boolean;
  onCheck: () => void;
  onExplainAgain: () => void;
  onContinue: () => void;
  onBack: () => void;
}

const TEACH_BACK_FORM_ID = 'teach-back-form';

// C8 (optional): the customer says the plan in their own words, typed or spoken, and sees
// whether it matches. Continue and Skip both go on to consent; nothing here is a gate.
export function TeachBackScreen(props: TeachBackScreenProps) {
  const { t } = useTranslation();
  const answerId = useId();
  const hasAnswer = props.answerText.trim() !== '';
  // Checks the answer without leaving the screen.
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (hasAnswer && !props.isChecking) props.onCheck();
  }
  return (
    <ScreenLayout
      onBack={props.onBack}
      stepLabel={t('teachBack.optional')}
      footer={
        <div className="flex flex-col gap-1">
          <Button size="large" isFullWidth onClick={props.onContinue}>
            {t('teachBack.continue')}
          </Button>
          <Button variant="quiet" isFullWidth onClick={props.onContinue}>
            {t('teachBack.skip')}
          </Button>
        </div>
      }
    >
      <div className="flex flex-col gap-2">
        <ScreenTitle>{t('teachBack.title')}</ScreenTitle>
        <p className="text-body text-slate">{t('teachBack.sub')}</p>
      </div>
      <p className="rounded-card bg-white px-4 py-3 text-body">
        <span className="text-slate">{t('teachBack.chosen')}</span>{' '}
        <strong className="text-deep-navy">
          {t('plan.nameWithTenure', {
            planName: t(getPlanNameKey(props.plan.emiType)),
            count: props.plan.tenureInMonths,
          })}
        </strong>
      </p>
      <form id={TEACH_BACK_FORM_ID} onSubmit={handleSubmit} className="flex flex-col gap-2">
        <label htmlFor={answerId} className="text-label text-deep-navy">
          {t('teachBack.answerLabel')}
        </label>
        <textarea
          id={answerId}
          rows={3}
          maxLength={MAXIMUM_ANSWER_LENGTH}
          value={props.answerText}
          placeholder={t('teachBack.answerPlaceholder')}
          onChange={(event) => {
            props.onChangeAnswerText(event.target.value);
          }}
          className="w-full resize-none rounded-card border-2 border-border bg-white px-4 py-3 text-lead text-deep-navy outline-none focus:border-cyan"
        />
        <Button
          type="submit"
          variant="secondary"
          className="self-start"
          disabled={!hasAnswer || props.isChecking}
        >
          {props.isChecking ? t('teachBack.checking') : t('teachBack.check')}
        </Button>
      </form>
      {props.voiceSection}
      <div aria-live="polite">
        {props.outcome === undefined ? null : (
          <TeachBackResultCard outcome={props.outcome} onExplainAgain={props.onExplainAgain} />
        )}
        {props.hasCheckFailed ? (
          <p className="text-body text-slate">{t('teachBack.checkFailed')}</p>
        ) : null}
      </div>
    </ScreenLayout>
  );
}
