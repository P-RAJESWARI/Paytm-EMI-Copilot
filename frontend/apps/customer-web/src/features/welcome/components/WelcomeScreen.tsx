import { formatRupeesFromPaise, type SupportedLanguage } from '@emi-copilot/shared-i18n';
import { Button, Card } from '@emi-copilot/ui-kit';
import { useTranslation } from 'react-i18next';

import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { ScreenTitle } from '../../../shared/components/ScreenTitle';
import { LanguageChoice } from './LanguageChoice';

export interface WelcomeScreenProps {
  shopName: string;
  productName: string;
  priceInPaise: number;
  selectedLanguage: SupportedLanguage;
  onSelectLanguage: (language: SupportedLanguage) => void;
  onStart: () => void;
}

// C1: the shop, the item and its price, the language choice, one line on data use, and Start.
export function WelcomeScreen({
  shopName,
  productName,
  priceInPaise,
  selectedLanguage,
  onSelectLanguage,
  onStart,
}: WelcomeScreenProps) {
  const { t } = useTranslation();
  return (
    <ScreenLayout
      footer={
        <Button variant="primary" size="large" isFullWidth onClick={onStart}>
          {t('welcome.start')}
        </Button>
      }
    >
      <Card className="flex items-center gap-3">
        <div className="flex flex-1 flex-col">
          <p className="text-label font-normal text-slate">{t('welcome.atShop', { shopName })}</p>
          <p className="text-body font-bold">{productName}</p>
        </div>
        <p className="text-title tabular-nums text-navy">{formatRupeesFromPaise(priceInPaise)}</p>
      </Card>
      <div className="flex flex-col gap-2">
        <ScreenTitle>{t('welcome.title')}</ScreenTitle>
        <p className="text-body text-slate">{t('welcome.subtitle')}</p>
      </div>
      <LanguageChoice
        heading={t('welcome.chooseLanguage')}
        options={[
          { language: 'ta', label: t('welcome.tamilOption') },
          { language: 'en', label: t('welcome.englishOption') },
        ]}
        selectedLanguage={selectedLanguage}
        onSelectLanguage={onSelectLanguage}
      />
      <p className="rounded-input bg-white p-3 text-label font-normal text-ink-muted">
        {t('welcome.dataUse')}
      </p>
    </ScreenLayout>
  );
}
