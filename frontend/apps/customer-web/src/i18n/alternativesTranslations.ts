import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of C6 (smarter alternatives), from the C6 mockup. Figures are the engine's
// (ADR 0020). Down payment and cheaper model need the shop's help (ADR 0022 decision 1).
export const ALTERNATIVES_ENGLISH_TRANSLATIONS = {
  alternatives: {
    title: 'Ways to lower the monthly amount',
    subtitle: 'Try one. The numbers update here.',
    loading: 'Finding ways to lower the monthly amount',
    yourPlan: 'Plan you are looking at',
    bandShare: '{{band}}, {{percent}} of monthly inflow.',
    withinYourBudget: 'Within your {{budget}} budget.',
    aboveYourBudget: '{{amount}} above your {{budget}} budget.',
    optionsLabel: 'Ways to try',
    chip: {
      DOWN_PAYMENT: 'Add a {{amount}} down payment',
      LONGER_TENURE: 'Longer tenure',
      CHEAPER_MODEL: 'Cheaper model',
    },
    was: 'Was {{amount}}',
    downPaymentName: '{{planName}}, {{amount}} down',
    cheaperModelName: '{{productName}}, {{price}}',
    downPaymentNote: 'You pay {{downPayment}} at the shop, then {{monthly}} a month.',
    longerTenureNote: 'It costs {{extra}} extra in total.',
    cheaperModelNote: '{{planName}} on the smaller model.',
    askShopTitle: 'Ask the shop to set this up',
    askShopDownPayment:
      'The shop can help you pay the down payment at the counter. It cannot be confirmed on this phone.',
    askShopCheaperModel: 'The shop starts a new sale for this model and shows you a new QR.',
    chooseThisPlan: 'Choose this plan',
    nothingBetter: 'No other way lowers the monthly amount for this plan.',
    nothingChosen: 'Nothing is chosen until you confirm on the last step.',
    continue: 'Continue',
  },
} as const;

// Tamil strings of C6, from the C6 mockup where it has them; the compiler checks the keys.
export const ALTERNATIVES_TAMIL_TRANSLATIONS: TranslationsMatching<
  typeof ALTERNATIVES_ENGLISH_TRANSLATIONS
> = {
  alternatives: {
    title: 'மாதத் தொகையைக் குறைக்கும் வழிகள்', // draft: needs native review
    subtitle: 'ஒன்றை முயற்சிக்கவும். எண்கள் இங்கேயே மாறும்.', // draft: needs native review
    loading: 'மாதத் தொகையைக் குறைக்கும் வழிகளைத் தேடுகிறோம்', // draft: needs native review
    yourPlan: 'நீங்கள் பார்க்கும் திட்டம்', // draft: needs native review
    bandShare: '{{band}}, மாத வரவில் {{percent}}.', // draft: needs native review
    withinYourBudget: 'உங்கள் {{budget}} பட்ஜெட்டுக்குள்.', // draft: needs native review
    aboveYourBudget: 'உங்கள் {{budget}} பட்ஜெட்டை விட {{amount}} அதிகம்.', // draft: needs native review
    optionsLabel: 'முயற்சிக்கும் வழிகள்', // draft: needs native review
    chip: {
      DOWN_PAYMENT: '{{amount}} முன்பணம் சேர்', // draft: needs native review
      LONGER_TENURE: 'நீண்ட காலம்', // draft: needs native review
      CHEAPER_MODEL: 'விலை குறைந்த மாடல்', // draft: needs native review
    },
    was: 'முன்பு {{amount}}', // draft: needs native review
    downPaymentName: '{{planName}}, {{amount}} முன்பணம்', // draft: needs native review
    cheaperModelName: '{{productName}}, {{price}}', // draft: needs native review
    downPaymentNote: 'கடையில் {{downPayment}} செலுத்துங்கள், பிறகு மாதம் {{monthly}}.', // draft: needs native review
    longerTenureNote: 'மொத்தத்தில் {{extra}} கூடுதல்.', // draft: needs native review
    cheaperModelNote: 'சிறிய மாடலில் {{planName}}.', // draft: needs native review
    askShopTitle: 'இதை அமைக்கக் கடையிடம் கேளுங்கள்', // draft: needs native review
    askShopDownPayment:
      'முன்பணத்தைக் கவுண்டரில் செலுத்தக் கடை உதவும். இதை இந்த போனில் உறுதிசெய்ய முடியாது.', // draft: needs native review
    askShopCheaperModel: 'இந்த மாடலுக்குக் கடை புதிய விற்பனையைத் தொடங்கி, புதிய QR-ஐக் காட்டும்.', // draft: needs native review
    chooseThisPlan: 'இந்தத் திட்டத்தைத் தேர்ந்தெடு', // draft: needs native review
    nothingBetter: 'இந்தத் திட்டத்தின் மாதத் தொகையைக் குறைக்க வேறு வழி இல்லை.', // draft: needs native review
    nothingChosen: 'கடைசிப் படியில் நீங்கள் உறுதிசெய்யும் வரை எதுவும் தேர்வாகாது.', // draft: needs native review
    continue: 'தொடர்க', // draft: needs native review
  },
};
