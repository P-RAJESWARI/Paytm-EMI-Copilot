import type { SpeechPurpose } from './CustomerFlowApi';
import type {
  CustomerPlanResponse,
  SpeechTranscriptionResponse,
  TeachBackResponse,
  TeachBackResult,
} from './customerContractTypes';

// Layer 4 sample answers for the fixture: what the speech, synthesis and teach-back calls give
// against the DESIGN_SPEC section 4 data. The real checks run on the server.

/** What the fixture "hears" for each purpose: ₹3,000 for the budget, plan A's terms for C8. */
export const FIXTURE_TRANSCRIPTIONS: Record<SpeechPurpose, SpeechTranscriptionResponse> = {
  BUDGET: {
    transcript: 'three thousand rupees',
    recognisedAmountInPaise: 300000,
    isLikelyMisheard: false,
  },
  TEACH_BACK: {
    transcript: 'I pay 3,667 every month for 6 months',
    recognisedAmountInPaise: null,
    isLikelyMisheard: false,
  },
};

/** The C8 result wording by result and language, from the C8 mockup's close-enough card. */
const TEACH_BACK_WORDING: Record<
  TeachBackResult,
  Record<'en' | 'ta', { title: string; body: string }>
> = {
  CLOSE_ENOUGH: {
    en: {
      title: 'That is right',
      body: 'You will pay ₹3,667 every month for 6 months. Nothing extra on top of ₹22,000.',
    },
    ta: {
      title: 'சரியாகச் சொன்னீர்கள்',
      body: 'நீங்கள் 6 மாதங்களுக்கு ஒவ்வொரு மாதமும் ₹3,667 செலுத்துவீர்கள். ₹22,000-க்கு மேல் கூடுதல் இல்லை.',
    },
  },
  TRY_AGAIN: {
    en: {
      title: 'Nearly there',
      body: 'You will pay ₹3,667 every month for 6 months. Nothing extra on top of ₹22,000.',
    },
    ta: {
      title: 'கிட்டத்தட்ட சரி',
      body: 'நீங்கள் 6 மாதங்களுக்கு ஒவ்வொரு மாதமும் ₹3,667 செலுத்துவீர்கள். ₹22,000-க்கு மேல் கூடுதல் இல்லை.',
    },
  },
};

// Answers C8 like the server's sample: an answer naming the plan's monthly figure is close
// enough; anything else is "try again" with what was heard.
export function buildFixtureTeachBack(
  plan: CustomerPlanResponse,
  answerText: string,
  language: 'en' | 'ta',
): TeachBackResponse {
  const monthlyRupeeDigits = String(Math.round(plan.monthlyInstallmentInPaise / 100));
  const numbersInAnswer: readonly string[] =
    answerText.replace(/(\d),(?=\d)/g, '$1').match(/\d+/g) ?? [];
  const result: TeachBackResult = numbersInAnswer.includes(monthlyRupeeDigits)
    ? 'CLOSE_ENOUGH'
    : 'TRY_AGAIN';
  return {
    result,
    ...TEACH_BACK_WORDING[result][language],
    heardText: result === 'TRY_AGAIN' ? answerText : null,
    highlightedAmounts: [
      { kind: 'MONTHLY_INSTALLMENT', amountInPaise: plan.monthlyInstallmentInPaise },
      { kind: 'EXTRA_IN_TOTAL', amountInPaise: plan.extraInTotalInPaise },
    ],
  };
}

/** A valid, silent 8 kHz mono WAV with no samples: enough for an audio element to load. */
const SILENT_WAV_HEADER_BYTES = [
  0x52, 0x49, 0x46, 0x46, 0x24, 0x00, 0x00, 0x00, 0x57, 0x41, 0x56, 0x45, 0x66, 0x6d, 0x74, 0x20,
  0x10, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x40, 0x1f, 0x00, 0x00, 0x80, 0x3e, 0x00, 0x00,
  0x02, 0x00, 0x10, 0x00, 0x64, 0x61, 0x74, 0x61, 0x00, 0x00, 0x00, 0x00,
];

// Gives the fixture's spoken explanation: a tiny silent WAV.
export function buildFixtureSilentWav(): Blob {
  return new Blob([new Uint8Array(SILENT_WAV_HEADER_BYTES)], { type: 'audio/wav' });
}
