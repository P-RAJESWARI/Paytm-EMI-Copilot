// The visible words the customer end-to-end tests press and read, in English and Tamil, copied from
// the customer-web translation tables (apps/customer-web/src/i18n). Figures are the design sample's.

/** The words of one language that the shared customer steps need. */
export interface CustomerWords {
  language: 'en' | 'ta';
  /** The language's button inside C1's "Choose your language" group. */
  languageChoice: string;
  start: string;
  budgetTitle: string;
  budgetAmountLabel: string;
  budgetContinue: string;
  budgetConfirmQuestion: string;
  budgetConfirmYes: string;
  comfortConsentTitle: string;
  comfortAllow: string;
  /** The Skip button's name starts with this word (its note is part of the name). */
  comfortSkip: string;
  plansTitle: string;
  plansContinue: string;
  noCostPlanRadio: string;
  alternativesTitle: string;
  alternativesContinue: string;
  explanationTitle: string;
  explanationContinue: string;
  consentTitle: string;
  planSummaryHeading: string;
  sendOtp: string;
  otpGroupForPhoneEnding42: string;
  firstOtpDigit: string;
  wrongOtpWithTwoTriesLeft: string;
  confirm: string;
  receiptReadyTitle: string;
  receiptReference: string;
  sessionUnavailableTitle: string;
  bandWords: { comfortable: string; stretching: string; risky: string };
  /** English interface words that must not show on a Tamil screen; undefined for English. */
  otherLanguageInterfaceWords: RegExp | undefined;
}

/** C1's language group, named in whichever language the page opened in. */
export const LANGUAGE_CHOICE_GROUP_NAME = /^(Choose your language|மொழியைத் தேர்ந்தெடுக்கவும்)$/;

export const ENGLISH_CUSTOMER_WORDS: CustomerWords = {
  language: 'en',
  languageChoice: 'English',
  start: 'Start',
  budgetTitle: 'What monthly amount feels comfortable?',
  budgetAmountLabel: 'Monthly amount',
  budgetContinue: 'Continue',
  budgetConfirmQuestion: 'You said ₹3,000. Correct?',
  budgetConfirmYes: 'Yes, correct',
  comfortConsentTitle: 'Check if a plan fits your month?',
  comfortAllow: 'Allow',
  comfortSkip: 'Skip',
  plansTitle: 'Your EMI options',
  plansContinue: 'Continue',
  noCostPlanRadio: 'No-cost EMI Brand, 6 months',
  alternativesTitle: 'Ways to lower the monthly amount',
  alternativesContinue: 'Continue',
  explanationTitle: 'Your plan in plain words',
  explanationContinue: 'Continue to confirm',
  consentTitle: 'Check and confirm your plan',
  planSummaryHeading: 'Your plan',
  sendOtp: 'Send OTP',
  otpGroupForPhoneEnding42: 'Enter the 6-digit OTP sent to your phone ending 42',
  firstOtpDigit: 'Digit 1 of 6',
  wrongOtpWithTwoTriesLeft:
    'That OTP does not match. Check the message and try again. 2 tries left.',
  confirm: 'Confirm',
  receiptReadyTitle: 'Your plan is ready',
  receiptReference: 'Reference',
  sessionUnavailableTitle: 'Ask the shop for a new QR',
  bandWords: { comfortable: 'Comfortable', stretching: 'Stretching', risky: 'Risky' },
  otherLanguageInterfaceWords: undefined,
};

export const TAMIL_CUSTOMER_WORDS: CustomerWords = {
  language: 'ta',
  languageChoice: 'தமிழ்',
  start: 'தொடங்கு',
  budgetTitle: 'மாதம் எவ்வளவு செலுத்துவது உங்களுக்கு வசதியாக இருக்கும்?',
  budgetAmountLabel: 'மாதத் தொகை',
  budgetContinue: 'தொடர்க',
  budgetConfirmQuestion: 'நீங்கள் சொன்னது ₹3,000. சரியா?',
  budgetConfirmYes: 'ஆம், சரி',
  comfortConsentTitle: 'திட்டம் உங்கள் மாதத்துக்குப் பொருந்துமா எனப் பார்க்கலாமா?',
  comfortAllow: 'அனுமதி',
  comfortSkip: 'தவிர்',
  plansTitle: 'உங்கள் EMI வாய்ப்புகள்',
  plansContinue: 'தொடர்க',
  noCostPlanRadio: 'கட்டணமில்லா EMI Brand, 6 மாதங்கள்',
  alternativesTitle: 'மாதத் தொகையைக் குறைக்கும் வழிகள்',
  alternativesContinue: 'தொடர்க',
  explanationTitle: 'உங்கள் திட்டம், எளிய வார்த்தைகளில்',
  explanationContinue: 'உறுதிசெய்யத் தொடர்க',
  consentTitle: 'உங்கள் திட்டத்தைச் சரிபார்த்து உறுதிசெய்யுங்கள்',
  planSummaryHeading: 'உங்கள் திட்டம்',
  sendOtp: 'OTP அனுப்பு',
  otpGroupForPhoneEnding42: '42-ல் முடியும் உங்கள் போனுக்கு வந்த 6 இலக்க OTP-ஐ உள்ளிடவும்',
  firstOtpDigit: 'இலக்கம் 1 / 6',
  wrongOtpWithTwoTriesLeft:
    'இந்த OTP பொருந்தவில்லை. செய்தியைப் பார்த்து மீண்டும் முயற்சிக்கவும். இன்னும் 2 முறை.',
  confirm: 'உறுதிசெய்',
  receiptReadyTitle: 'உங்கள் திட்டம் தயார்',
  receiptReference: 'குறிப்பு எண்',
  sessionUnavailableTitle: 'கடையிடம் புதிய QR கேளுங்கள்',
  bandWords: { comfortable: 'வசதியானது', stretching: 'கொஞ்சம் சிரமம்', risky: 'அதிக சுமை' },
  // Shop, product and lender names are data and stay as the shop entered them, so only interface
  // words are listed; EMI, OTP and Paytm are written in Latin letters in Tamil too.
  otherLanguageInterfaceWords:
    /\b(?:Start|Continue|Allow|Skip|Each month|Extra in total|Choose your language|Send OTP|Confirm|Your plan|Your EMI options|Step \d|Reference|Comfortable|Stretching|Risky|a month|months?)\b/,
};
