import type { TranslationsMatching } from './translationTree';

/** i18next namespace of the strings both apps share. */
export const SHARED_NAMESPACE = 'shared';

// English strings used by both apps. Sale status keys equal the API's SaleStatus values.
export const SHARED_ENGLISH_TRANSLATIONS = {
  common: {
    appName: 'EMI Copilot',
    loading: 'Loading…',
    tryAgain: 'Try again',
    somethingWentWrong: 'Something did not load. Please try again.',
    seeDetails: 'See details',
    hideDetails: 'Hide details',
    continue: 'Continue',
    back: 'Back',
    close: 'Close',
  },
  language: {
    groupLabel: 'Language',
    english: 'EN',
    tamil: 'தமிழ்',
  },
  saleStatus: {
    CHOOSING: 'Choosing',
    READY_TO_PAY: 'Ready to pay',
    PAID: 'Paid',
    PAYMENT_NOT_COMPLETED: 'Payment not completed',
    EXPIRED: 'Expired',
  },
  // The only three comfort bands (CLAUDE.md rule 5); keys equal the API's ComfortBand values.
  // Customer screens only: the merchant never sees a band (rule 6).
  comfortBand: {
    COMFORTABLE: 'Comfortable',
    STRETCHING: 'Stretching',
    RISKY: 'Risky',
  },
} as const;

// Tamil strings used by both apps. The compiler checks they have exactly the English keys.
export const SHARED_TAMIL_TRANSLATIONS: TranslationsMatching<typeof SHARED_ENGLISH_TRANSLATIONS> = {
  common: {
    appName: 'EMI Copilot', // draft: needs native review
    loading: 'ஏற்றுகிறது…', // draft: needs native review
    tryAgain: 'மீண்டும் முயற்சி', // draft: needs native review
    somethingWentWrong: 'சில தகவல்கள் ஏற்றப்படவில்லை. மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
    seeDetails: 'விவரங்களைப் பார்', // draft: needs native review
    hideDetails: 'விவரங்களை மறை', // draft: needs native review
    continue: 'தொடர்க', // draft: needs native review
    back: 'பின் செல்', // draft: needs native review
    close: 'மூடு', // draft: needs native review
  },
  language: {
    groupLabel: 'மொழி', // draft: needs native review
    english: 'EN', // draft: needs native review
    tamil: 'தமிழ்', // draft: needs native review
  },
  saleStatus: {
    CHOOSING: 'தேர்வு செய்கிறார்', // draft: needs native review
    READY_TO_PAY: 'பணம் செலுத்தத் தயார்', // draft: needs native review
    PAID: 'பணம் செலுத்தப்பட்டது', // draft: needs native review
    PAYMENT_NOT_COMPLETED: 'பணம் செலுத்துதல் முடியவில்லை', // draft: needs native review
    EXPIRED: 'காலாவதியானது', // draft: needs native review
  },
  comfortBand: {
    COMFORTABLE: 'வசதியானது', // draft: needs native review
    STRETCHING: 'கொஞ்சம் சிரமம்', // draft: needs native review
    RISKY: 'அதிக சுமை', // draft: needs native review
  },
};
