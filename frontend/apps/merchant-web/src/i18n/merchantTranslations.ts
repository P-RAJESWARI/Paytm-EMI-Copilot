import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

/** i18next namespace of the merchant app's own strings; shared strings live in shared-i18n. */
export const MERCHANT_NAMESPACE = 'merchant';

// English merchant strings (M1 brand panel for now; 2.6 adds the screens).
export const MERCHANT_ENGLISH_TRANSLATIONS = {
  brandPanel: {
    tagline: 'Help customers pick an EMI they understand.',
    description:
      'Start a session at the counter. The customer compares plans on their own phone, and you see where sales drop off.',
    audience: 'For shop counters',
  },
} as const;

// Tamil merchant strings; the compiler checks they have exactly the English keys.
export const MERCHANT_TAMIL_TRANSLATIONS: TranslationsMatching<
  typeof MERCHANT_ENGLISH_TRANSLATIONS
> = {
  brandPanel: {
    tagline: 'வாடிக்கையாளர்கள் புரிந்துகொள்ளும் EMI-யைத் தேர்ந்தெடுக்க உதவுங்கள்.', // draft: needs native review
    description:
      'கவுண்டரில் ஒரு அமர்வைத் தொடங்குங்கள். வாடிக்கையாளர் தங்கள் போனிலேயே திட்டங்களை ஒப்பிடுவார்; விற்பனை எங்கே நழுவுகிறது என்பதை நீங்கள் பார்ப்பீர்கள்.', // draft: needs native review
    audience: 'கடை கவுண்டர்களுக்காக', // draft: needs native review
  },
};
