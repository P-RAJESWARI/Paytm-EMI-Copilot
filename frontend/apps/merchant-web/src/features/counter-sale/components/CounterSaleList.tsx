import { Chip } from '@emi-copilot/ui-kit';
import { useId, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import type { SaleSummary } from '../api/counterSaleApi';
import { CounterSaleRow } from './CounterSaleRow';

export interface CounterSaleListProps {
  /** The sales, or undefined while loading or after an error. */
  sales: readonly SaleSummary[] | undefined;
  /** What to show instead of rows while loading or after an error. */
  placeholder?: ReactNode;
}

// The "At the counter now" column: heading with the customer count, one row per sale, and the
// privacy note. Only status, product and code are shown; never customer details (rule 6).
export function CounterSaleList({ sales, placeholder }: CounterSaleListProps) {
  const { t } = useTranslation();
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id={headingId} className="text-title text-navy">
          {t('counterList.title')}
        </h2>
        {sales === undefined ? null : (
          <Chip tone="information">{t('counterList.customerCount', { count: sales.length })}</Chip>
        )}
      </div>
      {placeholder}
      {sales?.length === 0 ? (
        <p className="rounded-card bg-white p-4 text-body text-slate">{t('counterList.empty')}</p>
      ) : null}
      {sales !== undefined && sales.length > 0 ? (
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {sales.map((sale) => (
            <CounterSaleRow key={sale.saleId} sale={sale} />
          ))}
        </ul>
      ) : null}
      <p data-privacy-note className="text-label font-normal text-slate">
        {t('counterList.privacyNote')}
      </p>
    </section>
  );
}
