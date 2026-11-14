import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of M2 (new EMI sale and the counter list). No "Scan barcode" (plan Q20).
export const COUNTER_SALE_ENGLISH_TRANSLATIONS = {
  counterSale: {
    title: 'New EMI sale',
    description: 'Pick the product, then show the customer the QR code.',
    searchLabel: 'Search product',
    productsLabel: 'Products',
    loadingProducts: 'Loading products…',
    noProducts: 'No products in your list yet.',
    noProductsFound: 'No products match “{{search}}”.',
    offers: {
      none: 'No EMI plans right now',
      planCount_one: '{{count}} EMI plan',
      planCount_other: '{{count}} EMI plans',
      withNoExtraCost_one: '{{planSummary}}, {{count}} with no extra cost',
      withNoExtraCost_other: '{{planSummary}}, {{count}} with no extra cost',
    },
    pickProductHint: 'Pick a product to see its price.',
    priceAtCounterLabel: 'Price at counter for {{productName}}',
    showQr: 'Show QR to customer',
    startingSale: 'Starting…',
  },
  counterList: {
    title: 'At the counter now',
    customerCount_one: '{{count}} customer',
    customerCount_other: '{{count}} customers',
    loading: 'Loading the counter list…',
    empty: 'No customers at the counter yet. Start a new EMI sale when someone asks about EMI.',
    sessionCode: 'Code {{code}}',
    forCode: ', code {{code}}',
    choosingOnTheirPhone: 'Choosing on their phone',
    paidAt: 'Paid at {{time}}',
    takePayment: 'Take payment',
    showQr: 'Show QR',
    privacyNote: 'You see only what the customer chose. Their income and EMIs stay on their phone.',
  },
} as const;

// Tamil strings of M2; the compiler checks they have exactly the English keys.
export const COUNTER_SALE_TAMIL_TRANSLATIONS: TranslationsMatching<
  typeof COUNTER_SALE_ENGLISH_TRANSLATIONS
> = {
  counterSale: {
    title: 'புதிய EMI விற்பனை', // draft: needs native review
    description: 'பொருளைத் தேர்ந்தெடுத்து, வாடிக்கையாளருக்கு QR குறியீட்டைக் காட்டுங்கள்.', // draft: needs native review
    searchLabel: 'பொருளைத் தேடு', // draft: needs native review
    productsLabel: 'பொருட்கள்', // draft: needs native review
    loadingProducts: 'பொருட்கள் ஏற்றுகிறது…', // draft: needs native review
    noProducts: 'உங்கள் பட்டியலில் இன்னும் பொருட்கள் இல்லை.', // draft: needs native review
    noProductsFound: '“{{search}}” உடன் பொருந்தும் பொருள் இல்லை.', // draft: needs native review
    offers: {
      none: 'இப்போது EMI திட்டங்கள் இல்லை', // draft: needs native review
      planCount_one: '{{count}} EMI திட்டம்', // draft: needs native review
      planCount_other: '{{count}} EMI திட்டங்கள்', // draft: needs native review
      withNoExtraCost_one: '{{planSummary}}, {{count}} கூடுதல் செலவு இல்லாமல்', // draft: needs native review
      withNoExtraCost_other: '{{planSummary}}, {{count}} கூடுதல் செலவு இல்லாமல்', // draft: needs native review
    },
    pickProductHint: 'விலையைப் பார்க்க ஒரு பொருளைத் தேர்ந்தெடுக்கவும்.', // draft: needs native review
    priceAtCounterLabel: '{{productName}}-க்கான கவுண்டர் விலை', // draft: needs native review
    showQr: 'வாடிக்கையாளருக்கு QR காட்டு', // draft: needs native review
    startingSale: 'தொடங்குகிறது…', // draft: needs native review
  },
  counterList: {
    title: 'இப்போது கவுண்டரில்', // draft: needs native review
    customerCount_one: '{{count}} வாடிக்கையாளர்', // draft: needs native review
    customerCount_other: '{{count}} வாடிக்கையாளர்கள்', // draft: needs native review
    loading: 'கவுண்டர் பட்டியல் ஏற்றுகிறது…', // draft: needs native review
    empty:
      'இன்னும் கவுண்டரில் வாடிக்கையாளர்கள் இல்லை. யாராவது EMI பற்றிக் கேட்டால் புதிய EMI விற்பனையைத் தொடங்குங்கள்.', // draft: needs native review
    sessionCode: 'குறியீடு {{code}}', // draft: needs native review
    forCode: ', குறியீடு {{code}}', // draft: needs native review
    choosingOnTheirPhone: 'தங்கள் போனில் தேர்வு செய்கிறார்', // draft: needs native review
    paidAt: '{{time}}-க்குப் பணம் செலுத்தப்பட்டது', // draft: needs native review
    takePayment: 'பணம் பெறு', // draft: needs native review
    showQr: 'QR காட்டு', // draft: needs native review
    privacyNote:
      'வாடிக்கையாளர் தேர்ந்ததை மட்டுமே நீங்கள் பார்க்கிறீர்கள். அவர்களின் வருமானமும் EMI-களும் அவர்களின் போனிலேயே இருக்கும்.', // draft: needs native review
  },
};
