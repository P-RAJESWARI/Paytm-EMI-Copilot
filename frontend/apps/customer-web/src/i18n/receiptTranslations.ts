import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of C10 (handoff and receipt), from the C10 mockup. Status keys equal the API's
// ReceiptStatus values. The shop takes the payment on Paytm (CLAUDE.md rule 9); a payment that did
// not finish is "not completed", never "declined" (DESIGN_SPEC 7.5).
export const RECEIPT_ENGLISH_TRANSLATIONS = {
  receipt: {
    loading: 'Getting your receipt',
    status: {
      READY_TO_PAY: {
        title: 'Your plan is ready',
        body: 'Show this screen to the shop. The shop completes the payment on Paytm.',
      },
      PAID: {
        title: 'Your EMI is confirmed',
        body: 'You pay {{amount}} a month for {{count}} months.',
      },
      PAYMENT_PENDING: {
        title: 'Waiting for confirmation',
        body: 'This can take a few minutes. Please do not pay again.',
      },
      PAYMENT_NOT_COMPLETED: {
        title: 'Payment not completed',
        body: 'The payment did not go through. The shop can try the payment again with you, or help you.',
      },
    },
    planHeading: 'Your plan',
    product: 'Item',
    reference: 'Reference',
    coolingOff:
      'You can cancel within the cooling-off period. The shop and the lender can help with this.',
    checkStatus: 'Check status',
  },
} as const;

// Tamil strings of C10, from the C10 mockup; the compiler checks they have exactly the English keys.
export const RECEIPT_TAMIL_TRANSLATIONS: TranslationsMatching<typeof RECEIPT_ENGLISH_TRANSLATIONS> =
  {
    receipt: {
      loading: 'உங்கள் ரசீதைப் பெறுகிறோம்', // draft: needs native review
      status: {
        READY_TO_PAY: {
          title: 'உங்கள் திட்டம் தயார்', // draft: needs native review
          body: 'இந்தத் திரையைக் கடையிடம் காட்டுங்கள். கடை Paytm-ல் பணம் செலுத்துதலை முடிக்கும்.', // draft: needs native review
        },
        PAID: {
          title: 'உங்கள் EMI உறுதியானது', // draft: needs native review
          body: '{{count}} மாதங்களுக்கு மாதம் {{amount}} செலுத்துவீர்கள்.', // draft: needs native review
        },
        PAYMENT_PENDING: {
          title: 'உறுதிப்படுத்தலுக்காகக் காத்திருக்கிறோம்', // draft: needs native review
          body: 'சில நிமிடங்கள் ஆகலாம். தயவுசெய்து மீண்டும் பணம் செலுத்த வேண்டாம்.', // draft: needs native review
        },
        PAYMENT_NOT_COMPLETED: {
          title: 'பணம் செலுத்துதல் முடியவில்லை', // draft: needs native review
          body: 'பணம் செலுத்துதல் நடக்கவில்லை. கடை உங்களுடன் மீண்டும் முயற்சிக்கலாம், அல்லது உதவலாம்.', // draft: needs native review
        },
      },
      planHeading: 'உங்கள் திட்டம்', // draft: needs native review
      product: 'பொருள்', // draft: needs native review
      reference: 'குறிப்பு எண்', // draft: needs native review
      coolingOff:
        'குறிப்பிட்ட காலத்திற்குள் இதை ரத்து செய்யலாம். இதற்குக் கடையும் கடன் வழங்குநரும் உதவுவார்கள்.', // draft: needs native review
      checkStatus: 'நிலையைப் பார்', // draft: needs native review
    },
  };
