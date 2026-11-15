import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of C1 (welcome and language), from the C1 mockup.
export const WELCOME_ENGLISH_TRANSLATIONS = {
  welcome: {
    atShop: 'At {{shopName}}',
    title: 'Pay in EMIs, with every cost shown',
    subtitle:
      'See each plan’s monthly amount and the extra you pay in total. You choose; nothing is decided for you.',
    chooseLanguage: 'Choose your language',
    tamilOption: 'தமிழ்',
    englishOption: 'English',
    dataUse:
      'We use the price and the monthly amount you tell us. If you allow it, we also check your monthly inflow and EMIs. The shop cannot see these.',
    start: 'Start',
  },
} as const;

// Tamil strings of C1, from the C1 mockup; the compiler checks they have exactly the English keys.
export const WELCOME_TAMIL_TRANSLATIONS: TranslationsMatching<typeof WELCOME_ENGLISH_TRANSLATIONS> =
  {
    welcome: {
      atShop: '{{shopName}}', // draft: needs native review
      title: 'எல்லா செலவும் தெரிந்து EMI-யில் வாங்குங்கள்', // draft: needs native review
      subtitle:
        'ஒவ்வொரு திட்டத்தின் மாதத் தொகையும், மொத்தக் கூடுதல் செலவும் காட்டப்படும். முடிவு உங்களுடையது.', // draft: needs native review
      chooseLanguage: 'மொழியைத் தேர்ந்தெடுக்கவும்', // draft: needs native review
      tamilOption: 'தமிழ்', // draft: needs native review
      englishOption: 'English', // draft: needs native review
      dataUse:
        'விலையையும் நீங்கள் சொல்லும் மாதத் தொகையையும் பயன்படுத்துகிறோம். நீங்கள் அனுமதித்தால், உங்கள் மாத வரவு மற்றும் EMI-களையும் பார்ப்போம். இதைக் கடை பார்க்க முடியாது.', // draft: needs native review
      start: 'தொடங்கு', // draft: needs native review
    },
  };
