import { useTranslation } from 'react-i18next';

import { getProblemMessageKey } from '../../customer-flow';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import { ScreenLayout } from '../../../shared/components/ScreenLayout';
import { ReceiptScreen } from '../components/ReceiptScreen';
import { useCustomerReceipt } from '../hooks/useCustomerReceipt';

// C10: fetches the receipt (polling while the payment can change) and shows its loading, error and
// status states, in the language chosen on C1. There is no way back from here.
export function ReceiptContainer() {
  const { t } = useTranslation();
  const receiptQuery = useCustomerReceipt();
  let content;
  if (receiptQuery.isPending) {
    content = <LoadingSkeleton accessibleLabel={t('receipt.loading')} lineCount={5} />;
  } else if (receiptQuery.isError) {
    content = (
      <CalmErrorMessage
        message={t(getProblemMessageKey(receiptQuery.error))}
        retryLabel={t('common.tryAgain')}
        onRetry={() => void receiptQuery.refetch()}
      />
    );
  } else {
    content = (
      <ReceiptScreen
        receipt={receiptQuery.data}
        isRefreshing={receiptQuery.isFetching}
        onCheckStatus={() => void receiptQuery.refetch()}
      />
    );
  }
  return <ScreenLayout>{content}</ScreenLayout>;
}
