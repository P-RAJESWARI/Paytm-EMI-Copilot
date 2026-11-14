import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of the app shell: the M1 brand panel and the sidebar.
export const SHELL_ENGLISH_TRANSLATIONS = {
  brandPanel: {
    tagline: 'Help customers pick an EMI they understand.',
    description:
      'Start a session at the counter. The customer compares plans on their own phone, and you see where sales drop off.',
    audience: 'For shop counters',
  },
  shell: {
    navigationLabel: 'Main',
    newEmiSale: 'New EMI sale',
    salesReport: 'Sales report',
    shopCardLabel: 'This device',
    loadingShop: 'Loading shop…',
  },
} as const;

// Tamil strings of the app shell; the compiler checks they have exactly the English keys.
export const SHELL_TAMIL_TRANSLATIONS: TranslationsMatching<typeof SHELL_ENGLISH_TRANSLATIONS> = {
  brandPanel: {
    tagline: 'வாடிக்கையாளர்கள் புரிந்துகொள்ளும் EMI-யைத் தேர்ந்தெடுக்க உதவுங்கள்.', // draft: needs native review
    description:
      'கவுண்டரில் ஒரு அமர்வைத் தொடங்குங்கள். வாடிக்கையாளர் தங்கள் போனிலேயே திட்டங்களை ஒப்பிடுவார்; விற்பனை எங்கே நழுவுகிறது என்பதை நீங்கள் பார்ப்பீர்கள்.', // draft: needs native review
    audience: 'கடை கவுண்டர்களுக்காக', // draft: needs native review
  },
  shell: {
    navigationLabel: 'முதன்மை', // draft: needs native review
    newEmiSale: 'புதிய EMI விற்பனை', // draft: needs native review
    salesReport: 'விற்பனை அறிக்கை', // draft: needs native review
    shopCardLabel: 'இந்தச் சாதனம்', // draft: needs native review
    loadingShop: 'கடை விவரம் ஏற்றுகிறது…', // draft: needs native review
  },
};
