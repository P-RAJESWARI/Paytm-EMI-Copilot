import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of C8 (optional teach-back), from the C8 mockup; the result title and body
// come from the server in the customer's language.
export const TEACH_BACK_ENGLISH_TRANSLATIONS = {
  teachBack: {
    optional: 'Optional check',
    title: 'Tell us in your own words what you will pay each month.',
    sub: 'This is not a test. It helps make sure the plan is clear.',
    chosen: 'Plan you are looking at:',
    answerLabel: 'Your answer',
    answerPlaceholder: 'For example: I pay … every month for … months',
    microphone: 'Or tap and say it',
    typeInstead: 'Voice is not working right now. Please type your answer.',
    check: 'Check my answer',
    checking: 'Checking your answer',
    checkFailed: 'We could not check that just now. You can still continue.',
    heardLabel: 'What we heard:',
    highlightedAmounts: 'The numbers to remember',
    monthlyAmount: '{{amount}} a month',
    extraAmount: 'Extra {{amount}}',
    explainAgain: 'Explain it again',
    continue: 'Continue',
    skip: 'Skip this step',
    loading: 'Opening the check',
  },
} as const;

// Tamil strings of C8, from the C8 mockup; the compiler checks they have exactly the English keys.
export const TEACH_BACK_TAMIL_TRANSLATIONS: TranslationsMatching<
  typeof TEACH_BACK_ENGLISH_TRANSLATIONS
> = {
  teachBack: {
    optional: 'விருப்பச் சரிபார்ப்பு', // draft: needs native review
    title: 'ஒவ்வொரு மாதமும் எவ்வளவு செலுத்துவீர்கள் என்று உங்கள் வார்த்தைகளில் சொல்லுங்கள்.', // draft: needs native review
    sub: 'இது தேர்வு அல்ல. திட்டம் தெளிவாக இருக்கிறதா என்று பார்க்க உதவும்.', // draft: needs native review
    chosen: 'நீங்கள் பார்க்கும் திட்டம்:', // draft: needs native review
    answerLabel: 'உங்கள் பதில்', // draft: needs native review
    answerPlaceholder: 'உதாரணம்: மாதம் … , … மாதங்களுக்கு', // draft: needs native review
    microphone: 'அல்லது தட்டிச் சொல்லுங்கள்', // draft: needs native review
    typeInstead: 'குரல் இப்போது வேலை செய்யவில்லை. உங்கள் பதிலை உள்ளிடவும்.', // draft: needs native review
    check: 'என் பதிலைச் சரிபார்', // draft: needs native review
    checking: 'உங்கள் பதிலைச் சரிபார்க்கிறோம்', // draft: needs native review
    checkFailed: 'இப்போது சரிபார்க்க முடியவில்லை. நீங்கள் தொடரலாம்.', // draft: needs native review
    heardLabel: 'நாங்கள் கேட்டது:', // draft: needs native review
    highlightedAmounts: 'நினைவில் கொள்ள வேண்டிய எண்கள்', // draft: needs native review
    monthlyAmount: 'மாதம் {{amount}}', // draft: needs native review
    extraAmount: 'கூடுதல் {{amount}}', // draft: needs native review
    explainAgain: 'மீண்டும் விளக்கவும்', // draft: needs native review
    continue: 'தொடர்க', // draft: needs native review
    skip: 'இந்தப் படியைத் தவிர்', // draft: needs native review
    loading: 'சரிபார்ப்பைத் திறக்கிறோம்', // draft: needs native review
  },
};
