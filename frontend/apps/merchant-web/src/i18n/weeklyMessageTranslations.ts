import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English labels around the weekly message (M5 card, M8). The message text itself comes from
// the backend in both languages (plan Q14); "Listen" stays hidden until Layer 4.
export const WEEKLY_MESSAGE_ENGLISH_TRANSLATIONS = {
  weeklyMessage: {
    summaryHeading: 'This week in short',
    languageLabel: 'Message language',
    loading: 'Loading this week’s summary…',
    sendToPhone: 'Send to my phone',
    sending: 'Sending…',
    sentToPhone: 'Sent to your phone',
    openPhoneView: 'See it as on your phone',
  },
} as const;

// Tamil labels around the weekly message; the compiler checks they have exactly the English keys.
export const WEEKLY_MESSAGE_TAMIL_TRANSLATIONS: TranslationsMatching<
  typeof WEEKLY_MESSAGE_ENGLISH_TRANSLATIONS
> = {
  weeklyMessage: {
    summaryHeading: 'இந்த வாரச் சுருக்கம்', // draft: needs native review
    languageLabel: 'செய்தியின் மொழி', // draft: needs native review
    loading: 'இந்த வாரச் சுருக்கம் ஏற்றுகிறது…', // draft: needs native review
    sendToPhone: 'என் போனுக்கு அனுப்பு', // draft: needs native review
    sending: 'அனுப்புகிறது…', // draft: needs native review
    sentToPhone: 'உங்கள் போனுக்கு அனுப்பப்பட்டது', // draft: needs native review
    openPhoneView: 'போனில் வருவது போல் பார்', // draft: needs native review
  },
};
