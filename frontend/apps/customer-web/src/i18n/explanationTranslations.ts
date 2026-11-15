import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of C7 (explanation), from the C7 mockup: the audited AI note or the standard
// note, Listen / Pause, and the way to C8. Never an error banner (DESIGN_SPEC 7.6).
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
    aiNote: 'Written by AI to explain the plans. It does not decide for you or approve anything.',
    listen: 'Listen to this',
    pause: 'Playing. Tap to pause.',
    preparingAudio: 'Getting the audio',
    checkUnderstanding: 'Check my understanding',
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
    aiNote:
      'திட்டங்களை விளக்க AI எழுதியது. இது உங்களுக்காக முடிவு எடுக்காது, எதையும் அங்கீகரிக்காது.', // draft: needs native review
    listen: 'கேளுங்கள்', // draft: needs native review
    pause: 'ஒலிக்கிறது. நிறுத்தத் தட்டவும்.', // draft: needs native review
    preparingAudio: 'ஒலியைப் பெறுகிறோம்', // draft: needs native review
    checkUnderstanding: 'நான் புரிந்துகொண்டதைச் சரிபார்', // draft: needs native review
  },
};
