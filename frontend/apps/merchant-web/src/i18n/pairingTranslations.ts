import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of M1 (pairing). The note asks the owner for the PIN (plan Q20, no "owner app").
export const PAIRING_ENGLISH_TRANSLATIONS = {
  pairing: {
    title: 'Pair this device',
    description: 'Enter your shop ID and the pairing PIN.',
    shopIdLabel: 'Shop ID',
    pinLabel: 'Pairing PIN',
    pinDigitLabel: 'PIN digit {{position}} of {{digitCount}}',
    submit: 'Pair device',
    submitting: 'Pairing…',
    noPinNote: 'No PIN? Ask the shop owner for the pairing PIN.',
    validation: {
      shopIdRequired: 'Enter your shop ID.',
      shopIdFormat: 'A shop ID has letters, numbers and dashes, like RAVI-0193.',
      pinIncomplete: 'Enter all 6 digits of the PIN.',
    },
    problems: {
      INVALID_PAIRING_CREDENTIALS:
        'That shop ID and PIN did not match. Please check both and try again.',
      PAIRING_TEMPORARILY_LOCKED_one:
        'Pairing is paused for this shop for about {{count}} minute. The shop owner can help if you need it sooner.',
      PAIRING_TEMPORARILY_LOCKED_other:
        'Pairing is paused for this shop for about {{count}} minutes. The shop owner can help if you need it sooner.',
      RATE_LIMITED_one:
        'This device has tried many times. Please wait about {{count}} minute and try again.',
      RATE_LIMITED_other:
        'This device has tried many times. Please wait about {{count}} minutes and try again.',
    },
  },
} as const;

// Tamil strings of M1; the compiler checks they have exactly the English keys.
export const PAIRING_TAMIL_TRANSLATIONS: TranslationsMatching<typeof PAIRING_ENGLISH_TRANSLATIONS> =
  {
    pairing: {
      title: 'இந்தச் சாதனத்தை இணைக்கவும்', // draft: needs native review
      description: 'உங்கள் கடை ஐடியையும் இணைப்பு PIN-ஐயும் உள்ளிடவும்.', // draft: needs native review
      shopIdLabel: 'கடை ஐடி', // draft: needs native review
      pinLabel: 'இணைப்பு PIN', // draft: needs native review
      pinDigitLabel: 'PIN இலக்கம் {{position}} / {{digitCount}}', // draft: needs native review
      submit: 'சாதனத்தை இணை', // draft: needs native review
      submitting: 'இணைக்கிறது…', // draft: needs native review
      noPinNote: 'PIN இல்லையா? இணைப்பு PIN-ஐக் கடை உரிமையாளரிடம் கேளுங்கள்.', // draft: needs native review
      validation: {
        shopIdRequired: 'உங்கள் கடை ஐடியை உள்ளிடவும்.', // draft: needs native review
        shopIdFormat: 'கடை ஐடியில் எழுத்துகள், எண்கள், கோடுகள் இருக்கும், எ.கா. RAVI-0193.', // draft: needs native review
        pinIncomplete: 'PIN-இன் 6 இலக்கங்களையும் உள்ளிடவும்.', // draft: needs native review
      },
      problems: {
        INVALID_PAIRING_CREDENTIALS:
          'இந்தக் கடை ஐடியும் PIN-உம் பொருந்தவில்லை. இரண்டையும் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
        PAIRING_TEMPORARILY_LOCKED_one:
          'இந்தக் கடைக்கான இணைப்பு சுமார் {{count}} நிமிடம் நிறுத்தப்பட்டுள்ளது. விரைவில் தேவைப்பட்டால் கடை உரிமையாளர் உதவலாம்.', // draft: needs native review
        PAIRING_TEMPORARILY_LOCKED_other:
          'இந்தக் கடைக்கான இணைப்பு சுமார் {{count}} நிமிடங்கள் நிறுத்தப்பட்டுள்ளது. விரைவில் தேவைப்பட்டால் கடை உரிமையாளர் உதவலாம்.', // draft: needs native review
        RATE_LIMITED_one:
          'இந்தச் சாதனம் பலமுறை முயன்றுள்ளது. சுமார் {{count}} நிமிடம் காத்திருந்து மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
        RATE_LIMITED_other:
          'இந்தச் சாதனம் பலமுறை முயன்றுள்ளது. சுமார் {{count}} நிமிடங்கள் காத்திருந்து மீண்டும் முயற்சிக்கவும்.', // draft: needs native review
      },
    },
  };
