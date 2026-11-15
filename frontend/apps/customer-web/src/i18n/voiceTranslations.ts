import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of the microphone itself, shared by C2 and C8 (Layer 4).
export const VOICE_ENGLISH_TRANSLATIONS = {
  voice: {
    tapToStop: 'Listening. Tap to stop.',
    uploading: 'Getting what you said',
  },
} as const;

// Tamil strings of the microphone; the compiler checks they have exactly the English keys.
export const VOICE_TAMIL_TRANSLATIONS: TranslationsMatching<typeof VOICE_ENGLISH_TRANSLATIONS> = {
  voice: {
    tapToStop: 'கேட்கிறோம். நிறுத்தத் தட்டவும்.', // draft: needs native review
    uploading: 'நீங்கள் சொன்னதைப் பெறுகிறோம்', // draft: needs native review
  },
};
