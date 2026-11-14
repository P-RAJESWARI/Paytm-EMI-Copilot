import { useId } from 'react';
import { useTranslation } from 'react-i18next';

import type { SuggestedActionText } from '../model/describeSuggestedAction';

export interface SuggestedActionsCardProps {
  actions: readonly SuggestedActionText[];
}

// "What you can do to sell more": each API suggestion as a bold line and its figures.
export function SuggestedActionsCard({ actions }: SuggestedActionsCardProps) {
  const { t } = useTranslation();
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded-card bg-white p-6 shadow-card"
    >
      <h2 id={headingId} className="text-title text-navy">
        {t('report.actions.title')}
      </h2>
      {actions.length === 0 ? (
        <p className="text-body text-slate">{t('report.actions.none')}</p>
      ) : (
        <ul className="m-0 grid list-none gap-3 p-0 md:grid-cols-2">
          {actions.map((action) => (
            <li key={action.title} className="flex flex-col gap-1 rounded-input bg-light-blue p-4">
              <strong className="text-body text-deep-navy">{action.title}</strong>
              {action.detail === '' ? null : (
                <span className="text-body text-slate">{action.detail}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
