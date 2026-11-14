import { useTranslation } from 'react-i18next';

import { CounterListContainer, NewEmiSaleContainer } from '../features/counter-sale';
import { PageHeading } from '../shared/components/PageHeading';

// M2 route: pick a product on the left, see the customers at the counter on the right.
export function NewEmiSalePage() {
  const { t } = useTranslation();
  return (
    <>
      <PageHeading title={t('counterSale.title')} description={t('counterSale.description')} />
      <div className="grid gap-6 md:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <NewEmiSaleContainer />
        <CounterListContainer />
      </div>
    </>
  );
}
