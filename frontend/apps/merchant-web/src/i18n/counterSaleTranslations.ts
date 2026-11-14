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
  showQr: {
    title: 'Show this QR to the customer',
    saleLine: '{{productName}}, {{price}}. Code {{code}}.',
    backToCounterList: 'Back to counter list',
    loadingSale: 'Loading the sale…',
    issuingQr: 'Making the QR code…',
    qrAccessibleLabel: 'Session QR code {{code}}',
    qrCaption: 'Opens on their phone. No app needed.',
    qrExpired: 'This QR code has expired. Show a new one if the customer still needs to scan.',
    showNewQr: 'Show a new QR',
    qrNotNeeded: 'This sale no longer needs a QR code.',
    serveOthersNote:
      'You can serve other customers meanwhile. This customer stays in your counter list and shows “Ready to pay” when they agree to a plan.',
    takePayment: 'Take payment',
    status: {
      CHOOSING: {
        title: 'The customer is choosing a plan on their phone',
        body: 'Nothing for you to do yet. Let them take their time.',
      },
      READY_TO_PAY: {
        title: 'The customer agreed to a plan',
        body: 'Take the payment with the exact plan below.',
      },
      PAYMENT_NOT_COMPLETED: {
        title: 'The payment was not completed',
        body: 'Nothing was confirmed. You can take the payment again with the same plan.',
      },
      PAID: {
        title: 'Paid',
        body: 'The payment is confirmed. You can hand over the product.',
      },
      EXPIRED: {
        title: 'This session has ended',
        body: 'The customer did not agree to a plan in time. Start a new EMI sale if they still want one.',
      },
    },
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
  showQr: {
    title: 'இந்த QR-ஐ வாடிக்கையாளருக்குக் காட்டுங்கள்', // draft: needs native review
    saleLine: '{{productName}}, {{price}}. குறியீடு {{code}}.', // draft: needs native review
    backToCounterList: 'கவுண்டர் பட்டியலுக்குத் திரும்பு', // draft: needs native review
    loadingSale: 'விற்பனை விவரம் ஏற்றுகிறது…', // draft: needs native review
    issuingQr: 'QR குறியீடு உருவாகிறது…', // draft: needs native review
    qrAccessibleLabel: 'அமர்வு QR குறியீடு {{code}}', // draft: needs native review
    qrCaption: 'அவர்களின் போனில் திறக்கும். ஆப் தேவையில்லை.', // draft: needs native review
    qrExpired:
      'இந்த QR குறியீட்டின் நேரம் முடிந்தது. வாடிக்கையாளர் இன்னும் ஸ்கேன் செய்ய வேண்டுமெனில் புதியதைக் காட்டுங்கள்.', // draft: needs native review
    showNewQr: 'புதிய QR காட்டு', // draft: needs native review
    qrNotNeeded: 'இந்த விற்பனைக்கு இனி QR குறியீடு தேவையில்லை.', // draft: needs native review
    serveOthersNote:
      'இதற்கிடையில் மற்ற வாடிக்கையாளர்களைக் கவனிக்கலாம். இந்த வாடிக்கையாளர் உங்கள் கவுண்டர் பட்டியலில் இருப்பார்; ஒரு திட்டத்தை ஏற்றதும் “பணம் செலுத்தத் தயார்” எனக் காட்டும்.', // draft: needs native review
    takePayment: 'பணம் பெறு', // draft: needs native review
    status: {
      CHOOSING: {
        title: 'வாடிக்கையாளர் தங்கள் போனில் திட்டத்தைத் தேர்வு செய்கிறார்', // draft: needs native review
        body: 'இப்போது நீங்கள் செய்ய வேண்டியது எதுவும் இல்லை. அவர்கள் நிதானமாகத் தேர்வு செய்யட்டும்.', // draft: needs native review
      },
      READY_TO_PAY: {
        title: 'வாடிக்கையாளர் ஒரு திட்டத்தை ஏற்றுக்கொண்டார்', // draft: needs native review
        body: 'கீழே உள்ள அதே திட்டத்தில் பணத்தைப் பெறுங்கள்.', // draft: needs native review
      },
      PAYMENT_NOT_COMPLETED: {
        title: 'பணம் செலுத்துதல் முடியவில்லை', // draft: needs native review
        body: 'எதுவும் உறுதிசெய்யப்படவில்லை. அதே திட்டத்தில் மீண்டும் பணம் பெறலாம்.', // draft: needs native review
      },
      PAID: {
        title: 'பணம் செலுத்தப்பட்டது', // draft: needs native review
        body: 'பணம் உறுதிசெய்யப்பட்டது. பொருளை ஒப்படைக்கலாம்.', // draft: needs native review
      },
      EXPIRED: {
        title: 'இந்த அமர்வு முடிந்தது', // draft: needs native review
        body: 'வாடிக்கையாளர் நேரத்தில் திட்டத்தை ஏற்கவில்லை. அவர்கள் இன்னும் விரும்பினால் புதிய EMI விற்பனையைத் தொடங்குங்கள்.', // draft: needs native review
      },
    },
  },
};
