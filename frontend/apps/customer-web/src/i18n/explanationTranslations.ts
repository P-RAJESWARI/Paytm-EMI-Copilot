import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of C7 (explanation), from the C7 mockup. Layer 3 shows the standard (template)
// text only: no audio, no teach-back (Layer 4), and never an error banner (DESIGN_SPEC 7.6).
export const EXPLANATION_ENGLISH_TRANSLATIONS = {
  explanation: {
    title: 'Your plan in plain words',
    loading: 'Getting the explanation',
    standardNote: 'Showing the standard plan details.',
    highlightedAmounts: 'The two numbers to remember',
    monthlyAmount: '{{amount}} a month',
    extraAmount: '{{amount}} extra in total',
    recapTitle: 'Plan you chose',
    continue: 'Continue to confirm',
  },
} as const;

// Tamil strings of C7, from the C7 mockup; the compiler checks they have exactly the English keys.
export const EXPLANATION_TAMIL_TRANSLATIONS: TranslationsMatching<
  typeof EXPLANATION_ENGLISH_TRANSLATIONS
> = {
  explanation: {
    title: 'உங்கள் திட்டம், எளிய வார்த்தைகளில்', // draft: needs native review
    loading: 'விளக்கத்தைப் பெறுகிறோம்', // draft: needs native review
    standardNote: 'நிலையான திட்ட விவரங்கள் காட்டப்படுகின்றன.', // draft: needs native review
    highlightedAmounts: 'நினைவில் கொள்ள வேண்டிய இரண்டு எண்கள்', // draft: needs native review
    monthlyAmount: 'மாதம் {{amount}}', // draft: needs native review
    extraAmount: 'மொத்தக் கூடுதல் {{amount}}', // draft: needs native review
    recapTitle: 'நீங்கள் தேர்ந்தெடுத்த திட்டம்', // draft: needs native review
    continue: 'உறுதிசெய்யத் தொடர்க', // draft: needs native review
  },
};
