import { formatRupeesFromPaise } from '@emi-copilot/shared-i18n';
import { useTranslation } from 'react-i18next';

import type { AlternativeKind, PlanAlternative } from '../../customer-flow';

export interface AlternativeChipsProps {
  alternatives: readonly PlanAlternative[];
  selectedKind: AlternativeKind | undefined;
  onToggleKind: (kind: AlternativeKind) => void;
}

// C6's "try one" chips: real toggle buttons (aria-pressed), 48 px tall, one per alternative the
// server found; pressing a pressed chip hides its numbers again.
export function AlternativeChips({
  alternatives,
  selectedKind,
  onToggleKind,
}: AlternativeChipsProps) {
  const { t } = useTranslation();
  return (
    <div role="group" aria-label={t('alternatives.optionsLabel')} className="flex flex-wrap gap-2">
      {alternatives.map((alternative) => {
        const isSelected = alternative.kind === selectedKind;
        return (
          <button
            key={alternative.kind}
            type="button"
            aria-pressed={isSelected}
            onClick={() => {
              onToggleKind(alternative.kind);
            }}
            className={`min-h-touch-target rounded-input border-2 px-3 text-body font-semibold text-navy ${
              isSelected ? 'border-cyan bg-cyan-tint' : 'border-border bg-white'
            }`}
          >
            {t(`alternatives.chip.${alternative.kind}`, {
              amount: formatRupeesFromPaise(alternative.downPaymentInPaise),
            })}
          </button>
        );
      })}
    </div>
  );
}
