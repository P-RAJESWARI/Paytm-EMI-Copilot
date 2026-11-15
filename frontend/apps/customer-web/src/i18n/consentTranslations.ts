import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of C9 (consent and OTP), from the C9 mockup. Calm OTP wording, no lockout or
// blame (DESIGN_SPEC 7.4); the cooling-off line is a placeholder until the lender confirms it.
export const CONSENT_ENGLISH_TRANSLATIONS = {
  consent: {
    title: 'Check and confirm your plan',
    summaryHeading: 'Your plan',
    otpIntro: 'We send a one-time password (OTP) to your phone to confirm it is you.',
    sendOtp: 'Send OTP',
    otpLabel: 'Enter the 6-digit OTP sent to your phone ending {{lastTwoDigits}}',
    otpDigit: 'Digit {{position}} of {{count}}',
    resendIn: 'You can ask for a new OTP in {{time}}',
    resend: 'Send a new OTP',
    wrongOtp: 'That OTP does not match. Check the message and try again.',
    wrongOtpWithTries_one: 'That OTP does not match. Check the message and try again. 1 try left.',
    wrongOtpWithTries_other:
      'That OTP does not match. Check the message and try again. {{count}} tries left.',
    expiredOtp: 'This OTP has expired. Ask for a new one.',
    coolingOff: 'You can cancel within the cooling-off period.',
    agreement:
      'By confirming, you agree to this plan. The payment happens next on Paytm, with the shop. We never ask for card details here.',
    confirm: 'Confirm',
  },
} as const;

// Tamil strings of C9, from the C9 mockup; the compiler checks they have exactly the English keys.
export const CONSENT_TAMIL_TRANSLATIONS: TranslationsMatching<typeof CONSENT_ENGLISH_TRANSLATIONS> =
  {
    consent: {
      title: 'உங்கள் திட்டத்தைச் சரிபார்த்து உறுதிசெய்யுங்கள்', // draft: needs native review
      summaryHeading: 'உங்கள் திட்டம்', // draft: needs native review
      otpIntro:
        'இது நீங்கள்தான் என உறுதிசெய்ய, உங்கள் போனுக்கு ஒருமுறை கடவுச்சொல் (OTP) அனுப்புவோம்.', // draft: needs native review
      sendOtp: 'OTP அனுப்பு', // draft: needs native review
      otpLabel: '{{lastTwoDigits}}-ல் முடியும் உங்கள் போனுக்கு வந்த 6 இலக்க OTP-ஐ உள்ளிடவும்', // draft: needs native review
      otpDigit: 'இலக்கம் {{position}} / {{count}}', // draft: needs native review
      resendIn: '{{time}}-க்குப் பிறகு புதிய OTP கேட்கலாம்', // draft: needs native review
      resend: 'புதிய OTP அனுப்பு', // draft: needs native review
      wrongOtp: 'இந்த OTP பொருந்தவில்லை. செய்தியைப் பார்த்து மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
      wrongOtpWithTries_one:
        'இந்த OTP பொருந்தவில்லை. செய்தியைப் பார்த்து மீண்டும் முயற்சிக்கவும். இன்னும் 1 முறை.', // draft: needs native review
      wrongOtpWithTries_other:
        'இந்த OTP பொருந்தவில்லை. செய்தியைப் பார்த்து மீண்டும் முயற்சிக்கவும். இன்னும் {{count}} முறை.', // draft: needs native review
      expiredOtp: 'இந்த OTP காலாவதியாகிவிட்டது. புதியதைக் கேளுங்கள்.', // draft: needs native review
      coolingOff: 'குறிப்பிட்ட காலத்திற்குள் இதை ரத்து செய்யலாம்.', // draft: needs native review
      agreement:
        'உறுதிசெய்வதன் மூலம் இந்தத் திட்டத்துக்கு ஒப்புக்கொள்கிறீர்கள். அடுத்து கடையுடன் Paytm-ல் பணம் செலுத்தப்படும். இங்கே கார்டு விவரங்களை நாங்கள் கேட்பதில்லை.', // draft: needs native review
      confirm: 'உறுதிசெய்', // draft: needs native review
    },
  };
