import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of C3 (comfort check consent) and C5 (comfort detail), from those mockups.
// The check is advice, never a credit decision (security-and-compliance.md section 6).
export const COMFORT_ENGLISH_TRANSLATIONS = {
  comfortConsent: {
    title: 'Check if a plan fits your month?',
    why: 'This shows how much of your monthly money each plan would take.',
    readIntro: 'If you allow, we read only:',
    readInflow: 'Average money coming in each month',
    readExistingEmis: 'EMIs you already pay',
    onlyForThis: 'Used only for this check, for this purchase.',
    shopCannotSee: 'The shop cannot see this information.',
    adviceOnly: 'This is advice to help you choose. It is not a loan decision.',
    allow: 'Allow',
    skip: 'Skip',
    skipNote: 'You can still compare all plans',
  },
  comfortDetail: {
    heading: 'Comfort detail',
    withThisPlan: 'With this plan, your EMIs take {{percent}} of your monthly inflow.',
    currentShare: 'Your current EMIs already take {{percent}}.',
    barLabel: 'EMIs you pay now {{current}}, with this plan {{total}}',
    currentEmis: 'EMIs you pay now',
    thisPlan: 'This plan',
    inflow: 'Money coming in each month',
    amountWithShare: '{{amount}} ({{percent}})',
    howTitle: 'How we read this',
    belowLower: 'Below 35%: Comfortable',
    betweenLowerAndUpper: '35% to 50%: Stretching',
    aboveUpper: 'Above 50%: Risky',
    guide: 'A guide to help you choose, not a loan decision.',
    backToPlans: 'Back to plans',
  },
} as const;

// Tamil strings of C3 and C5, from the mockups; the compiler checks they have exactly the English keys.
export const COMFORT_TAMIL_TRANSLATIONS: TranslationsMatching<typeof COMFORT_ENGLISH_TRANSLATIONS> =
  {
    comfortConsent: {
      title: 'திட்டம் உங்கள் மாதத்துக்குப் பொருந்துமா எனப் பார்க்கலாமா?', // draft: needs native review
      why: 'ஒவ்வொரு திட்டமும் உங்கள் மாதப் பணத்தில் எவ்வளவு எடுக்கும் என்று இது காட்டும்.', // draft: needs native review
      readIntro: 'நீங்கள் அனுமதித்தால், இவற்றை மட்டும் பார்ப்போம்:', // draft: needs native review
      readInflow: 'ஒவ்வொரு மாதமும் வரும் சராசரி பணம்', // draft: needs native review
      readExistingEmis: 'நீங்கள் ஏற்கனவே செலுத்தும் EMI-கள்', // draft: needs native review
      onlyForThis: 'இந்த வாங்குதலுக்கான சோதனைக்கு மட்டுமே பயன்படும்.', // draft: needs native review
      shopCannotSee: 'இந்தத் தகவலை கடை பார்க்க முடியாது.', // draft: needs native review
      adviceOnly: 'இது தேர்வு செய்ய உதவும் ஆலோசனை மட்டுமே. கடன் முடிவு அல்ல.', // draft: needs native review
      allow: 'அனுமதி', // draft: needs native review
      skip: 'தவிர்', // draft: needs native review
      skipNote: 'தவிர்த்தாலும் எல்லா திட்டங்களையும் ஒப்பிடலாம்', // draft: needs native review
    },
    comfortDetail: {
      heading: 'வசதி விவரம்', // draft: needs native review
      withThisPlan: 'இந்தத் திட்டத்துடன், உங்கள் EMI-கள் மாத வரவில் {{percent}} எடுக்கும்.', // draft: needs native review
      currentShare: 'உங்கள் தற்போதைய EMI-கள் ஏற்கனவே {{percent}} எடுக்கின்றன.', // draft: needs native review
      barLabel: 'இப்போது செலுத்தும் EMI-கள் {{current}}, இந்தத் திட்டத்துடன் {{total}}', // draft: needs native review
      currentEmis: 'இப்போது செலுத்தும் EMI-கள்', // draft: needs native review
      thisPlan: 'இந்தத் திட்டம்', // draft: needs native review
      inflow: 'ஒவ்வொரு மாதமும் வரும் பணம்', // draft: needs native review
      amountWithShare: '{{amount}} ({{percent}})', // draft: needs native review
      howTitle: 'இதை எப்படிப் படிப்பது', // draft: needs native review
      belowLower: '35%-க்குக் கீழ்: வசதியானது', // draft: needs native review
      betweenLowerAndUpper: '35% முதல் 50%: கொஞ்சம் சிரமம்', // draft: needs native review
      aboveUpper: '50%-க்கு மேல்: அதிக சுமை', // draft: needs native review
      guide: 'தேர்வு செய்ய உதவும் வழிகாட்டி மட்டுமே, கடன் முடிவு அல்ல.', // draft: needs native review
      backToPlans: 'திட்டங்களுக்குத் திரும்பு', // draft: needs native review
    },
  };
