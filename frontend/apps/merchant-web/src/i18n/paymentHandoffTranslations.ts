import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of M4 (take payment). EDC steps only (plan Q5); the link is shown, not sent
// (plan Q6); a failed payment is "not completed", never "declined" (spec 7.5).
export const PAYMENT_HANDOFF_ENGLISH_TRANSLATIONS = {
  handoff: {
    title: 'Take payment on Paytm',
    description: 'Use the exact offer the customer chose so the price matches.',
    loading: 'Loading the payment details…',
    notReady:
      'This sale is not ready for payment yet. The customer is still choosing on their phone.',
    planGridLabel: 'Chosen plan details',
    chosenPlan: 'Chosen plan',
    product: 'Product',
    price: 'Price',
    planNameInSentence: { NO_COST: 'no-cost EMI', STANDARD: 'EMI' },
    edc: {
      title: 'On the EDC machine',
      programme: { BRAND_EMI: 'Brand EMI', BANK_EMI: 'Bank EMI' },
      tenure_one: '{{count}} month',
      tenure_other: '{{count}} months',
      tenureNoCost_one: '{{count}} month, no-cost',
      tenureNoCost_other: '{{count}} months, no-cost',
      stepChooseProgramme: 'Choose <strong>{{programme}}</strong>.',
      stepPickProduct: 'Pick <strong>{{productName}}</strong> and <strong>{{tenure}}</strong>.',
      stepCheckAmount:
        'Check the amount is <strong>{{amount}}</strong>, then hand it to the customer.',
    },
    link: {
      noEdc: 'No EDC at hand?',
      send: 'Send payment link',
      sending: 'Making the link…',
      title: 'Payment link',
      caption: 'The customer scans this to pay on Paytm. Nothing is sent from this tablet.',
      qrLabel: 'Payment link QR code',
      urlLabel: 'Link to copy',
      copy: 'Copy link',
      copied: 'Copied',
      copyUnavailable:
        'Copying is not available on this device. Select the link above and copy it.',
    },
    status: {
      heading: 'Payment status',
      refreshing: 'Checking…',
      WAITING: {
        title: 'Waiting for payment',
        body: 'This updates when the server confirms the payment. Don’t hand over the product yet.',
        action: 'Refresh status',
      },
      PAID: {
        title: 'Paid',
        body: 'Confirmed by the server at {{time}}. {{amount}} on {{planName}}. You can hand over the product.',
        bodyWithoutTime:
          'Confirmed by the server. {{amount}} on {{planName}}. You can hand over the product.',
        action: 'Back to counter list',
      },
      NOT_COMPLETED: {
        title: 'Payment not completed',
        body: 'Nothing was confirmed. Ask the customer if they want to try again, or send a payment link.',
        action: 'Try again',
      },
    },
  },
} as const;

// Tamil strings of M4; the compiler checks they have exactly the English keys.
export const PAYMENT_HANDOFF_TAMIL_TRANSLATIONS: TranslationsMatching<
  typeof PAYMENT_HANDOFF_ENGLISH_TRANSLATIONS
> = {
  handoff: {
    title: 'Paytm-இல் பணம் பெறுங்கள்', // draft: needs native review
    description: 'விலை பொருந்த, வாடிக்கையாளர் தேர்ந்த அதே சலுகையைப் பயன்படுத்துங்கள்.', // draft: needs native review
    loading: 'பணம் செலுத்தும் விவரங்கள் ஏற்றுகிறது…', // draft: needs native review
    notReady:
      'இந்த விற்பனை இன்னும் பணம் செலுத்தத் தயாராகவில்லை. வாடிக்கையாளர் இன்னும் தங்கள் போனில் தேர்வு செய்கிறார்.', // draft: needs native review
    planGridLabel: 'தேர்ந்த திட்ட விவரங்கள்', // draft: needs native review
    chosenPlan: 'தேர்ந்த திட்டம்', // draft: needs native review
    product: 'பொருள்', // draft: needs native review
    price: 'விலை', // draft: needs native review
    planNameInSentence: {
      NO_COST: 'கட்டணமில்லா EMI', // draft: needs native review
      STANDARD: 'EMI', // draft: needs native review
    },
    edc: {
      title: 'EDC இயந்திரத்தில்', // draft: needs native review
      programme: {
        BRAND_EMI: 'Brand EMI', // draft: needs native review
        BANK_EMI: 'Bank EMI', // draft: needs native review
      },
      tenure_one: '{{count}} மாதம்', // draft: needs native review
      tenure_other: '{{count}} மாதங்கள்', // draft: needs native review
      tenureNoCost_one: '{{count}} மாதம், கட்டணமில்லா', // draft: needs native review
      tenureNoCost_other: '{{count}} மாதங்கள், கட்டணமில்லா', // draft: needs native review
      stepChooseProgramme: '<strong>{{programme}}</strong>-ஐத் தேர்ந்தெடுக்கவும்.', // draft: needs native review
      stepPickProduct:
        '<strong>{{productName}}</strong>, <strong>{{tenure}}</strong> ஆகியவற்றைத் தேர்ந்தெடுக்கவும்.', // draft: needs native review
      stepCheckAmount:
        'தொகை <strong>{{amount}}</strong> என்பதைச் சரிபார்த்து, வாடிக்கையாளரிடம் கொடுங்கள்.', // draft: needs native review
    },
    link: {
      noEdc: 'EDC இயந்திரம் இல்லையா?', // draft: needs native review
      send: 'பணம் செலுத்தும் இணைப்பை அனுப்பு', // draft: needs native review
      sending: 'இணைப்பு உருவாகிறது…', // draft: needs native review
      title: 'பணம் செலுத்தும் இணைப்பு', // draft: needs native review
      caption:
        'வாடிக்கையாளர் இதை ஸ்கேன் செய்து Paytm-இல் பணம் செலுத்துவார். இந்த டேப்லெட்டிலிருந்து எதுவும் அனுப்பப்படாது.', // draft: needs native review
      qrLabel: 'பணம் செலுத்தும் இணைப்பின் QR குறியீடு', // draft: needs native review
      urlLabel: 'நகலெடுக்க வேண்டிய இணைப்பு', // draft: needs native review
      copy: 'இணைப்பை நகலெடு', // draft: needs native review
      copied: 'நகலெடுக்கப்பட்டது', // draft: needs native review
      copyUnavailable:
        'இந்தச் சாதனத்தில் நகலெடுக்க முடியவில்லை. மேலே உள்ள இணைப்பைத் தேர்ந்தெடுத்து நகலெடுக்கவும்.', // draft: needs native review
    },
    status: {
      heading: 'பணம் செலுத்தும் நிலை', // draft: needs native review
      refreshing: 'சரிபார்க்கிறது…', // draft: needs native review
      WAITING: {
        title: 'பணத்திற்காகக் காத்திருக்கிறது', // draft: needs native review
        body: 'சர்வர் பணத்தை உறுதிசெய்ததும் இது புதுப்பிக்கப்படும். இப்போதே பொருளை ஒப்படைக்க வேண்டாம்.', // draft: needs native review
        action: 'நிலையைப் புதுப்பி', // draft: needs native review
      },
      PAID: {
        title: 'பணம் செலுத்தப்பட்டது', // draft: needs native review
        body: '{{time}}-க்கு சர்வர் உறுதிசெய்தது. {{planName}}-இல் {{amount}}. பொருளை ஒப்படைக்கலாம்.', // draft: needs native review
        bodyWithoutTime: 'சர்வர் உறுதிசெய்தது. {{planName}}-இல் {{amount}}. பொருளை ஒப்படைக்கலாம்.', // draft: needs native review
        action: 'கவுண்டர் பட்டியலுக்குத் திரும்பு', // draft: needs native review
      },
      NOT_COMPLETED: {
        title: 'பணம் செலுத்துதல் முடியவில்லை', // draft: needs native review
        body: 'எதுவும் உறுதிசெய்யப்படவில்லை. வாடிக்கையாளர் மீண்டும் முயல விரும்புகிறாரா என்று கேளுங்கள், அல்லது பணம் செலுத்தும் இணைப்பை அனுப்புங்கள்.', // draft: needs native review
        action: 'மீண்டும் முயற்சி', // draft: needs native review
      },
    },
  },
};
