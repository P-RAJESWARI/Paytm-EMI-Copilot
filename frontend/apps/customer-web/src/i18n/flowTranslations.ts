import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings shared by every customer screen: step labels, the session screen and calm
// problem messages (never the server's English detail; api-conventions.md section 4).
export const FLOW_ENGLISH_TRANSLATIONS = {
  flow: {
    stepOf: 'Step {{current}} of {{total}}',
    confirmStep: 'Confirm',
    openingSession: 'Opening your EMI options…',
  },
  session: {
    unavailableTitle: 'Ask the shop for a new QR',
    unavailableBody:
      'This QR has already been used or has timed out. The shop can show you a new one to scan.',
  },
  problems: {
    generic: 'Something did not load. Please try again.',
    NETWORK_UNAVAILABLE: 'Your phone could not reach us. Check your internet and try again.',
    RATE_LIMITED: 'Please wait a moment, then try again.',
    PAYMENT_GATEWAY_UNAVAILABLE: 'The plans could not be fetched just now. Please try again.',
    PAYMENT_GATEWAY_TIMEOUT: 'The plans are taking too long to arrive. Please try again.',
    REQUEST_VALIDATION_FAILED: 'Please check what you typed and try again.',
  },
} as const;

// Tamil strings shared by every customer screen; the compiler checks they have exactly the English keys.
export const FLOW_TAMIL_TRANSLATIONS: TranslationsMatching<typeof FLOW_ENGLISH_TRANSLATIONS> = {
  flow: {
    stepOf: 'படி {{current}} / {{total}}', // draft: needs native review
    confirmStep: 'உறுதிசெய்', // draft: needs native review
    openingSession: 'உங்கள் EMI வாய்ப்புகளைத் திறக்கிறோம்…', // draft: needs native review
  },
  session: {
    unavailableTitle: 'கடையிடம் புதிய QR கேளுங்கள்', // draft: needs native review
    unavailableBody:
      'இந்த QR ஏற்கனவே பயன்படுத்தப்பட்டது அல்லது நேரம் முடிந்துவிட்டது. ஸ்கேன் செய்ய கடை புதியதைக் காட்டும்.', // draft: needs native review
  },
  problems: {
    generic: 'சில தகவல்கள் ஏற்றப்படவில்லை. மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
    NETWORK_UNAVAILABLE:
      'உங்கள் போனால் எங்களை அடைய முடியவில்லை. இணையத்தைச் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
    RATE_LIMITED: 'சிறிது நேரம் காத்திருந்து மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
    PAYMENT_GATEWAY_UNAVAILABLE: 'இப்போது திட்டங்களைப் பெற முடியவில்லை. மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
    PAYMENT_GATEWAY_TIMEOUT: 'திட்டங்கள் வர நேரம் ஆகிறது. மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
    REQUEST_VALIDATION_FAILED: 'நீங்கள் உள்ளிட்டதைச் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
  },
};
