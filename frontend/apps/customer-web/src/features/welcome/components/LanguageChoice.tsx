import type { SupportedLanguage } from '@emi-copilot/shared-i18n';

export interface LanguageChoiceOption {
  language: SupportedLanguage;
  /** The language's own name, for example "தமிழ்". */
  label: string;
}

export interface LanguageChoiceProps {
  /** Translated "Choose your language". */
  heading: string;
  options: readonly LanguageChoiceOption[];
  selectedLanguage: SupportedLanguage;
  onSelectLanguage: (language: SupportedLanguage) => void;
}

// The large Tamil / English choice on C1: pressed-state buttons, 56 px tall, each in its own script.
export function LanguageChoice({
  heading,
  options,
  selectedLanguage,
  onSelectLanguage,
}: LanguageChoiceProps) {
  return (
    <div role="group" aria-labelledby="language-choice-heading" className="flex flex-col gap-2">
      <p id="language-choice-heading" className="text-label text-slate">
        {heading}
      </p>
      {options.map((option) => {
        const isSelected = option.language === selectedLanguage;
        return (
          <button
            key={option.language}
            type="button"
            lang={option.language}
            aria-pressed={isSelected}
            onClick={() => {
              onSelectLanguage(option.language);
            }}
            className={`flex min-h-touch-target-primary items-center justify-between rounded-input border-2 bg-white px-4 text-lead font-semibold text-navy ${
              isSelected ? 'border-cyan' : 'border-border'
            }`}
          >
            {option.label}
            <span
              aria-hidden="true"
              className={`box-border h-6 w-6 rounded-pill ${
                isSelected ? 'border-[7px] border-cyan' : 'border-2 border-border-strong'
              }`}
            />
          </button>
        );
      })}
    </div>
  );
}
