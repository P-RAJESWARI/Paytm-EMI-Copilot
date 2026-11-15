import { Button, Card } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { ScreenTitle } from '../../../shared/components/ScreenTitle';

export interface ComfortConsentScreenProps {
  isSaving: boolean;
  /** A calm, translated message when sending the answer failed. */
  errorMessage?: string | undefined;
  onAllow: () => void;
  onSkip: () => void;
  onBack: () => void;
}

// C3: why the check helps, the only two things read, that the shop cannot see them, that it is
// advice and not a loan decision, then Allow or Skip (skipping still compares every plan).
export function ComfortConsentScreen({
  isSaving,
  errorMessage,
  onAllow,
  onSkip,
  onBack,
}: ComfortConsentScreenProps) {
  const { t } = useTranslation();
  return (
    <ScreenLayout
      onBack={onBack}
      stepLabel={t('flow.stepOf', { current: 2, total: 4 })}
      footer={
        <>
          <Button size="large" isFullWidth onClick={onAllow} disabled={isSaving}>
            {t('comfortConsent.allow')}
          </Button>
          <Button variant="secondary" size="large" isFullWidth onClick={onSkip} disabled={isSaving}>
            <span className="flex flex-col">
              {t('comfortConsent.skip')}
              <span className="text-caption font-normal text-slate">
                {t('comfortConsent.skipNote')}
              </span>
            </span>
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-2">
        <ScreenTitle>{t('comfortConsent.title')}</ScreenTitle>
        <p className="text-body text-slate">{t('comfortConsent.why')}</p>
      </div>
      <Card className="flex flex-col gap-3">
        <p className="text-body font-semibold">{t('comfortConsent.readIntro')}</p>
        <ul className="flex list-disc flex-col gap-2 pl-6 text-body">
          <li>{t('comfortConsent.readInflow')}</li>
          <li>{t('comfortConsent.readExistingEmis')}</li>
        </ul>
        <p className="text-label font-normal text-slate">{t('comfortConsent.onlyForThis')}</p>
      </Card>
      <p className="rounded-input bg-comfortable-tint p-3 text-body font-semibold text-comfortable-text">
        {t('comfortConsent.shopCannotSee')}
      </p>
      <p className="text-body text-ink-muted">{t('comfortConsent.adviceOnly')}</p>
      {errorMessage === undefined ? null : <CalmErrorMessage message={errorMessage} />}
    </ScreenLayout>
  );
}
