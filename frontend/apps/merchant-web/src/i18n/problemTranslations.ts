import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English calm messages per API problem code, plus the plan wording shared by M3 and M4.
// Keys equal the API's stable problem codes; the server's English detail is never shown.
export const PROBLEM_ENGLISH_TRANSLATIONS = {
  problems: {
    generic: 'Something did not load. Please try again.',
    NETWORK_UNAVAILABLE:
      "Could not reach the server. Check the shop's internet connection and try again.",
    RATE_LIMITED: 'Too many requests just now. Please wait a minute and try again.',
    SALE_NOT_FOUND: 'We could not find this sale. Go back to the counter list.',
    PRODUCT_NOT_FOUND: 'This product is no longer in your list. Please pick it again.',
    SALE_STATE_CONFLICT: 'This sale has moved on. The latest status is shown.',
    SESSION_CODES_EXHAUSTED:
      'Many customers are open at the counter right now. Finish one, then try again.',
    CHOSEN_PLAN_NO_LONGER_OFFERED:
      'This plan is no longer offered at this price. Ask the customer to choose again on their phone.',
    PAYMENT_LINK_ALREADY_ACTIVE:
      'A payment link for this sale is still open. Use that link, or wait for it to finish.',
    PAYMENT_LINK_CREATION_IN_PROGRESS:
      'The payment link is still being made. Wait a moment, then refresh the status.',
    PAYMENT_LINK_OUTCOME_UNKNOWN:
      'We could not confirm whether the link was made. Refresh the status before trying again.',
    PAYMENT_LINK_CREATION_FAILED:
      'The payment link could not be made. Try again, or use the EDC machine.',
    PAYMENT_GATEWAY_TIMEOUT:
      'The payment service did not answer in time. Try again; it will not make a second link.',
    PAYMENT_GATEWAY_UNAVAILABLE:
      'The payment service is not available right now. Use the EDC machine or try again shortly.',
    PAYMENT_GATEWAY_REQUEST_REJECTED:
      'The payment service could not take this request. Use the EDC machine or try again shortly.',
    PAYMENT_GATEWAY_ERROR:
      'The payment service is not available right now. Use the EDC machine or try again shortly.',
    MERCHANT_AUTHENTICATION_REQUIRED: 'Please pair this device again.',
  },
  plan: {
    name: { NO_COST: 'No-cost EMI', STANDARD: 'EMI' },
    nameWithTenure_one: '{{planName}}, {{count}} month',
    nameWithTenure_other: '{{planName}}, {{count}} months',
    eachMonth: 'Each month',
    extraInTotal: 'Extra in total',
    total: 'Total',
    fundedBy: 'Funded by',
  },
} as const;

// Tamil problem messages and plan wording; the compiler checks they have exactly the English keys.
export const PROBLEM_TAMIL_TRANSLATIONS: TranslationsMatching<typeof PROBLEM_ENGLISH_TRANSLATIONS> =
  {
    problems: {
      generic: 'சில தகவல்கள் ஏற்றப்படவில்லை. மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
      NETWORK_UNAVAILABLE:
        'சர்வரை அணுக முடியவில்லை. கடையின் இணைய இணைப்பைச் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
      RATE_LIMITED:
        'இப்போது அதிகமான கோரிக்கைகள். ஒரு நிமிடம் காத்திருந்து மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
      SALE_NOT_FOUND:
        'இந்த விற்பனையைக் கண்டுபிடிக்க முடியவில்லை. கவுண்டர் பட்டியலுக்குத் திரும்புங்கள்.', // draft: needs native review
      PRODUCT_NOT_FOUND:
        'இந்தப் பொருள் இப்போது உங்கள் பட்டியலில் இல்லை. மீண்டும் தேர்ந்தெடுக்கவும்.', // draft: needs native review
      SALE_STATE_CONFLICT: 'இந்த விற்பனையின் நிலை மாறியுள்ளது. சமீபத்திய நிலை காட்டப்படுகிறது.', // draft: needs native review
      SESSION_CODES_EXHAUSTED:
        'இப்போது கவுண்டரில் பல வாடிக்கையாளர்கள் உள்ளனர். ஒன்றை முடித்து மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
      CHOSEN_PLAN_NO_LONGER_OFFERED:
        'இந்த விலையில் இந்தத் திட்டம் இப்போது வழங்கப்படவில்லை. வாடிக்கையாளரைத் தங்கள் போனில் மீண்டும் தேர்வு செய்யச் சொல்லுங்கள்.', // draft: needs native review
      PAYMENT_LINK_ALREADY_ACTIVE:
        'இந்த விற்பனைக்கான பணம் செலுத்தும் இணைப்பு இன்னும் திறந்துள்ளது. அதைப் பயன்படுத்துங்கள் அல்லது அது முடியும் வரை காத்திருங்கள்.', // draft: needs native review
      PAYMENT_LINK_CREATION_IN_PROGRESS:
        'பணம் செலுத்தும் இணைப்பு இன்னும் உருவாகிறது. சிறிது நேரம் காத்திருந்து நிலையைப் புதுப்பிக்கவும்.', // draft: needs native review
      PAYMENT_LINK_OUTCOME_UNKNOWN:
        'இணைப்பு உருவானதா என்பதை உறுதிசெய்ய முடியவில்லை. மீண்டும் முயலும் முன் நிலையைப் புதுப்பிக்கவும்.', // draft: needs native review
      PAYMENT_LINK_CREATION_FAILED:
        'பணம் செலுத்தும் இணைப்பை உருவாக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது EDC இயந்திரத்தைப் பயன்படுத்தவும்.', // draft: needs native review
      PAYMENT_GATEWAY_TIMEOUT:
        'பணம் செலுத்தும் சேவை நேரத்தில் பதிலளிக்கவில்லை. மீண்டும் முயற்சிக்கவும்; இரண்டாவது இணைப்பு உருவாகாது.', // draft: needs native review
      PAYMENT_GATEWAY_UNAVAILABLE:
        'பணம் செலுத்தும் சேவை இப்போது கிடைக்கவில்லை. EDC இயந்திரத்தைப் பயன்படுத்தவும் அல்லது சிறிது நேரத்தில் முயற்சிக்கவும்.', // draft: needs native review
      PAYMENT_GATEWAY_REQUEST_REJECTED:
        'பணம் செலுத்தும் சேவை இந்தக் கோரிக்கையை ஏற்கவில்லை. EDC இயந்திரத்தைப் பயன்படுத்தவும் அல்லது சிறிது நேரத்தில் முயற்சிக்கவும்.', // draft: needs native review
      PAYMENT_GATEWAY_ERROR:
        'பணம் செலுத்தும் சேவை இப்போது கிடைக்கவில்லை. EDC இயந்திரத்தைப் பயன்படுத்தவும் அல்லது சிறிது நேரத்தில் முயற்சிக்கவும்.', // draft: needs native review
      MERCHANT_AUTHENTICATION_REQUIRED: 'தயவுசெய்து இந்தச் சாதனத்தை மீண்டும் இணைக்கவும்.', // draft: needs native review
    },
    plan: {
      name: {
        NO_COST: 'கட்டணமில்லா EMI', // draft: needs native review
        STANDARD: 'EMI', // draft: needs native review
      },
      nameWithTenure_one: '{{planName}}, {{count}} மாதம்', // draft: needs native review
      nameWithTenure_other: '{{planName}}, {{count}} மாதங்கள்', // draft: needs native review
      eachMonth: 'ஒவ்வொரு மாதமும்', // draft: needs native review
      extraInTotal: 'மொத்தக் கூடுதல்', // draft: needs native review
      total: 'மொத்தம்', // draft: needs native review
      fundedBy: 'நிதி வழங்குபவர்', // draft: needs native review
    },
  };
