export interface LanguageToggleOption<Language extends string> {
  language: Language;
  /** The language's own short name, for example "EN" or "தமிழ்". */
  label: string;
}

/** `light` for white or light-blue backgrounds, `dark` for navy cards (M5 weekly message). */
export type LanguageToggleSurface = 'light' | 'dark';

export interface LanguageToggleProps<Language extends string> {
  /** Translated "Language", read by screen readers for the group. */
  accessibleLabel: string;
  options: readonly LanguageToggleOption<Language>[];
  selectedLanguage: Language;
  onSelectLanguage: (language: Language) => void;
  surface?: LanguageToggleSurface | undefined;
}

const SURFACE_CLASS_NAMES: Record<
  LanguageToggleSurface,
  { group: string; selected: string; unselected: string }
> = {
  light: {
    group: 'border border-border bg-white',
    selected: 'bg-navy text-white',
    unselected: 'bg-transparent text-navy',
  },
  dark: {
    group: 'bg-overlay-on-navy',
    selected: 'bg-white text-navy',
    unselected: 'bg-transparent text-white focus-visible:outline-cyan-soft',
  },
};

// The EN / தமிழ் switch: a labelled group of pressed-state buttons, at least 48 px tall.
export function LanguageToggle<Language extends string>({
  accessibleLabel,
  options,
  selectedLanguage,
  onSelectLanguage,
  surface = 'light',
}: LanguageToggleProps<Language>) {
  const surfaceClassNames = SURFACE_CLASS_NAMES[surface];
  return (
    <div
      role="group"
      aria-label={accessibleLabel}
      className={`inline-flex rounded-pill p-1 ${surfaceClassNames.group}`}
    >
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
            className={`min-h-touch-target min-w-14 rounded-pill px-3 text-label ${
              isSelected ? surfaceClassNames.selected : surfaceClassNames.unselected
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
