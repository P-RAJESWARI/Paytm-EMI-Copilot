import { useTranslation } from 'react-i18next';

import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { ScreenTitle } from '../../../shared/components/ScreenTitle';

// The calm end screen when the QR is used, expired or missing, or the session timed out: the
// only way on is a new QR from the shop (security-and-compliance.md section 4). No blame.
export function SessionUnavailableScreen() {
  const { t } = useTranslation();
  return (
    <ScreenLayout>
      <ScreenTitle>{t('session.unavailableTitle')}</ScreenTitle>
      <p className="text-body text-slate">{t('session.unavailableBody')}</p>
    </ScreenLayout>
  );
}
