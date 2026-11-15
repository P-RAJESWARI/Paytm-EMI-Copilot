import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of C2 (budget), from the C2 mockup, including the Layer 4 microphone states.
export const BUDGET_ENGLISH_TRANSLATIONS = {
  budget: {
    title: 'What monthly amount feels comfortable?',
    help: 'Think of what you can pay each month without worry.',
    amountLabel: 'Monthly amount',
    perMonth: 'a month',
    emptyHint: 'Type an amount to continue.',
    confirmQuestion: 'You said {{amount}}. Correct?',
    confirmYes: 'Yes, correct',
    edit: 'Edit',
    continue: 'Continue',
    emptyHintWithVoice: 'Type an amount or tap the microphone to continue.',
    microphone: 'Tap and say the amount',
    misheard: 'We heard {{amount}}.',
    noAmountHeard: 'We did not catch an amount.',
    misheardFix: 'If that is wrong, tap the amount above and type the right number.',
    sayAgain: 'Say it again',
    typeInstead: 'Voice is not working right now. Please type the amount.',
  },
} as const;

// Tamil strings of C2, from the C2 mockup; the compiler checks they have exactly the English keys.
export const BUDGET_TAMIL_TRANSLATIONS: TranslationsMatching<typeof BUDGET_ENGLISH_TRANSLATIONS> = {
  budget: {
    title: 'மாதம் எவ்வளவு செலுத்துவது உங்களுக்கு வசதியாக இருக்கும்?', // draft: needs native review
    help: 'கவலையின்றி ஒவ்வொரு மாதமும் செலுத்தக்கூடிய தொகையை நினைத்துப் பாருங்கள்.', // draft: needs native review
    amountLabel: 'மாதத் தொகை', // draft: needs native review
    perMonth: 'மாதம்', // draft: needs native review
    emptyHint: 'தொடர, ஒரு தொகையை உள்ளிடவும்.', // draft: needs native review
    confirmQuestion: 'நீங்கள் சொன்னது {{amount}}. சரியா?', // draft: needs native review
    confirmYes: 'ஆம், சரி', // draft: needs native review
    edit: 'மாற்று', // draft: needs native review
    continue: 'தொடர்க', // draft: needs native review
    emptyHintWithVoice: 'தொடர, ஒரு தொகையை உள்ளிடவும் அல்லது மைக்கைத் தட்டவும்.', // draft: needs native review
    microphone: 'தட்டி, தொகையைச் சொல்லுங்கள்', // draft: needs native review
    misheard: 'நாங்கள் கேட்டது {{amount}}.', // draft: needs native review
    noAmountHeard: 'தொகை எங்களுக்குக் கேட்கவில்லை.', // draft: needs native review
    misheardFix: 'அது தவறு என்றால், மேலே உள்ள தொகையைத் தட்டி சரியான எண்ணை உள்ளிடவும்.', // draft: needs native review
    sayAgain: 'மீண்டும் சொல்லுங்கள்', // draft: needs native review
    typeInstead: 'குரல் இப்போது வேலை செய்யவில்லை. தொகையை உள்ளிடவும்.', // draft: needs native review
  },
};
