import { useId } from 'react';
import { useTranslation } from 'react-i18next';

export interface ProductSearchFieldProps {
  searchText: string;
  onSearchTextChange: (searchText: string) => void;
}

// The labelled "Search product" box with a decorative magnifier.
export function ProductSearchField({ searchText, onSearchTextChange }: ProductSearchFieldProps) {
  const { t } = useTranslation();
  const inputId = useId();
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={inputId} className="text-label">
        {t('counterSale.searchLabel')}
      </label>
      <div className="flex min-h-touch-target items-center gap-2 rounded-input border-2 border-border bg-white px-3 focus-within:border-cyan">
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          aria-hidden="true"
          focusable="false"
          className="shrink-0 text-slate"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
        <input
          id={inputId}
          type="search"
          autoComplete="off"
          value={searchText}
          onChange={(event) => {
            onSearchTextChange(event.target.value);
          }}
          className="min-h-touch-target w-full min-w-0 bg-transparent text-body text-deep-navy outline-none"
        />
      </div>
    </div>
  );
}
