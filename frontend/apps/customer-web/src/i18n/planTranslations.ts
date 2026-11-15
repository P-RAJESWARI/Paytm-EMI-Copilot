import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of C4 (options comparison) and the plan wording every later screen reuses, from
// the C4 mockup. Plan names come from the EMI type plus the lender line (ADR 0022 decision 5).
export const PLAN_ENGLISH_TRANSLATIONS = {
  plan: {
    name: { NO_COST: 'No-cost EMI', STANDARD: 'EMI' },
    lenderWithTenure_one: '{{lenderLabel}}, {{count}} month',
    lenderWithTenure_other: '{{lenderLabel}}, {{count}} months',
    nameWithTenure_one: '{{planName}}, {{count}} month',
    nameWithTenure_other: '{{planName}}, {{count}} months',
    eachMonth: 'Each month',
    forMonths_one: 'for {{count}} month',
    forMonths_other: 'for {{count}} months',
    extraInTotal: 'Extra in total',
    onTopOfPrice: 'on top of {{price}}',
    totalInAll: 'You pay in all {{amount}}',
    total: 'Total you pay',
    tenure: 'Tenure',
    tenureMonths_one: '{{count}} month',
    tenureMonths_other: '{{count}} months',
    withinBudget: 'Within your budget',
    aboveBudget: '{{amount}} above your budget',
  },
  plans: {
    title: 'Your EMI options',
    productLine: '{{productName}}, {{price}}',
    sortedWithinBudget: 'Sorted by what fits your {{budget}} budget',
    sortedClosestToBudget: 'Sorted by what is closest to your {{budget}} budget',
    tradeOff:
      'The plan with nothing extra has a higher monthly amount. The lowest monthly amount costs more in total.',
    noFitTitle: 'No plan is within {{budget}} a month',
    noFitBody: 'All plans are shown below so you can still compare them.',
    noFitLink: 'See ways to lower the monthly amount',
    noFitChooseFirst: 'Choose a plan below to see ways to lower its monthly amount.',
    loading: 'Getting plans for this phone',
    empty: 'No EMI plans are offered for this item right now. Please ask the shop.',
    planChanged: 'A plan’s figures changed. Please check the plans again and choose one.',
    chooseToContinue: 'Choose a plan to continue.',
    comfortDetail: 'Comfort detail',
    comfortDetailFor: 'Comfort detail for {{planName}}',
    continue: 'Continue',
  },
} as const;

// Tamil strings of C4 and the plan wording, from the C4 mockup; the compiler checks the keys.
export const PLAN_TAMIL_TRANSLATIONS: TranslationsMatching<typeof PLAN_ENGLISH_TRANSLATIONS> = {
  plan: {
    name: {
      NO_COST: 'கட்டணமில்லா EMI', // draft: needs native review
      STANDARD: 'EMI', // draft: needs native review
    },
    lenderWithTenure_one: '{{lenderLabel}}, {{count}} மாதம்', // draft: needs native review
    lenderWithTenure_other: '{{lenderLabel}}, {{count}} மாதங்கள்', // draft: needs native review
    nameWithTenure_one: '{{planName}}, {{count}} மாதம்', // draft: needs native review
    nameWithTenure_other: '{{planName}}, {{count}} மாதங்கள்', // draft: needs native review
    eachMonth: 'ஒவ்வொரு மாதமும்', // draft: needs native review
    forMonths_one: '{{count}} மாதத்துக்கு', // draft: needs native review
    forMonths_other: '{{count}} மாதங்களுக்கு', // draft: needs native review
    extraInTotal: 'மொத்தக் கூடுதல்', // draft: needs native review
    onTopOfPrice: '{{price}}-க்கு மேல்', // draft: needs native review
    totalInAll: 'மொத்தம் செலுத்துவது {{amount}}', // draft: needs native review
    total: 'மொத்தம் நீங்கள் செலுத்துவது', // draft: needs native review
    tenure: 'காலம்', // draft: needs native review
    tenureMonths_one: '{{count}} மாதம்', // draft: needs native review
    tenureMonths_other: '{{count}} மாதங்கள்', // draft: needs native review
    withinBudget: 'உங்கள் பட்ஜெட்டுக்குள்', // draft: needs native review
    aboveBudget: 'பட்ஜெட்டை விட {{amount}} அதிகம்', // draft: needs native review
  },
  plans: {
    title: 'உங்கள் EMI வாய்ப்புகள்', // draft: needs native review
    productLine: '{{productName}}, {{price}}', // draft: needs native review
    sortedWithinBudget: 'உங்கள் {{budget}} பட்ஜெட்டுக்குப் பொருந்துவதன்படி வரிசை', // draft: needs native review
    sortedClosestToBudget: 'உங்கள் {{budget}} பட்ஜெட்டுக்கு அருகில் உள்ளதன்படி வரிசை', // draft: needs native review
    tradeOff:
      'கூடுதல் செலவு இல்லாத திட்டத்தில் மாதத் தொகை அதிகம். குறைந்த மாதத் தொகைக்கு மொத்தச் செலவு அதிகம்.', // draft: needs native review
    noFitTitle: 'மாதம் {{budget}}-க்குள் எந்தத் திட்டமும் இல்லை', // draft: needs native review
    noFitBody: 'ஒப்பிட்டுப் பார்க்க எல்லா திட்டங்களும் கீழே உள்ளன.', // draft: needs native review
    noFitLink: 'மாதத் தொகையைக் குறைக்கும் வழிகள்', // draft: needs native review
    noFitChooseFirst:
      'மாதத் தொகையைக் குறைக்கும் வழிகளைப் பார்க்க, கீழே ஒரு திட்டத்தைத் தேர்ந்தெடுக்கவும்.', // draft: needs native review
    loading: 'இந்த போனுக்கான திட்டங்களைப் பெறுகிறோம்', // draft: needs native review
    empty: 'இந்தப் பொருளுக்கு இப்போது EMI திட்டங்கள் இல்லை. கடையிடம் கேளுங்கள்.', // draft: needs native review
    planChanged:
      'ஒரு திட்டத்தின் எண்கள் மாறிவிட்டன. திட்டங்களை மீண்டும் பார்த்து ஒன்றைத் தேர்ந்தெடுக்கவும்.', // draft: needs native review
    chooseToContinue: 'தொடர ஒரு திட்டத்தைத் தேர்ந்தெடுக்கவும்.', // draft: needs native review
    comfortDetail: 'வசதி விவரம்', // draft: needs native review
    comfortDetailFor: '{{planName}}: வசதி விவரம்', // draft: needs native review
    continue: 'தொடர்க', // draft: needs native review
  },
};
