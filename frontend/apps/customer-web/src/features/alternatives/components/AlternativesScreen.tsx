import { Button } from '@emi-copilot/ui-kit';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { ScreenTitle } from '../../../shared/components/ScreenTitle';

export interface AlternativesScreenProps {
  /** The plan, the chips and the selected alternative, or the loading or error state. */
  children: ReactNode;
  onContinue: () => void;
  onBack: () => void;
}

// C6's frame: title, "try one", the content, the reassurance that nothing is chosen yet, Continue.
export function AlternativesScreen({ children, onContinue, onBack }: AlternativesScreenProps) {
  const { t } = useTranslation();
  return (
    <ScreenLayout
      onBack={onBack}
      stepLabel={t('flow.stepOf', { current: 3, total: 4 })}
      footer={
        <Button size="large" isFullWidth onClick={onContinue}>
          {t('alternatives.continue')}
        </Button>
      }
    >
      <div className="flex flex-col gap-2">
        <ScreenTitle>{t('alternatives.title')}</ScreenTitle>
        <p className="text-body text-slate">{t('alternatives.subtitle')}</p>
      </div>
      {children}
      <p className="text-label font-normal text-slate">{t('alternatives.nothingChosen')}</p>
    </ScreenLayout>
  );
}
