import { useTranslation } from 'react-i18next';

import { getProblemMessageKey } from '../../../shared/api/problemMessageKey';
import { CalmErrorMessage } from '../../../shared/components/CalmErrorMessage';
import { LoadingSkeleton } from '../../../shared/components/LoadingSkeleton';
import { CounterSaleList } from '../components/CounterSaleList';
import { useCounterSales } from '../hooks/useCounterSales';

// Container for M2's "At the counter now" column: loading, error, empty and the live list.
export function CounterListContainer() {
  const { t } = useTranslation();
  const counterSalesQuery = useCounterSales();
  let placeholder;
  if (counterSalesQuery.isPending) {
    placeholder = <LoadingSkeleton accessibleLabel={t('counterList.loading')} />;
  } else if (counterSalesQuery.isError) {
    placeholder = (
      <CalmErrorMessage
        message={t(getProblemMessageKey(counterSalesQuery.error))}
        retryLabel={t('common.tryAgain')}
        onRetry={() => void counterSalesQuery.refetch()}
      />
    );
  }
  return <CounterSaleList sales={counterSalesQuery.data} placeholder={placeholder} />;
}
