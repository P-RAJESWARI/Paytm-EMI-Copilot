import type { TranslationsMatching } from '@emi-copilot/shared-i18n';

// English strings of M5 with the M6 and M7 panels. Sentences are filled with API figures only;
// "Most who left…" became the biggest-drop line and the tip quotes the API's amounts (plan Q9).
export const SALES_REPORT_ENGLISH_TRANSLATIONS = {
  report: {
    title: 'Sales report',
    loading: 'Loading the sales report…',
    fewerThanFive: 'fewer than 5',
    range: { label: 'Period', TODAY: 'Today', THIS_WEEK: 'This week', THIS_MONTH: 'This month' },
    empty: {
      title: {
        TODAY: 'No EMI sales today yet',
        THIS_WEEK: 'No EMI sales this week yet',
        THIS_MONTH: 'No EMI sales this month yet',
      },
      body: 'When a customer asks about EMI, start a new EMI sale. Your report fills in as customers finish choosing.',
    },
    funnel: {
      title: 'Where customers drop off',
      stage: {
        STARTED: 'Started',
        BUDGET_TOLD: 'Told a budget',
        PLANS_VIEWED: 'Saw the plans',
        AGREED: 'Agreed to a plan',
        PAID: 'Paid',
      },
      afterStage: {
        STARTED: 'starting',
        BUDGET_TOLD: 'telling a budget',
        PLANS_VIEWED: 'seeing the plans',
        AGREED: 'agreeing to a plan',
        PAID: 'paying',
      },
      biggestDrop_one: '{{count}} customer left after {{stagePhrase}}. That is the biggest drop.',
      biggestDrop_other:
        '{{count}} customers left after {{stagePhrase}}. That is the biggest drop.',
      biggestDropWithoutCount: 'The biggest drop was after {{stagePhrase}}.',
    },
    missedSales: {
      title: 'Missed sales',
      panelLabel: 'Missed sales detail',
      none: 'No missed sales in this period.',
      headline_one:
        '{{count}} customer wanted under {{ceiling}} a month with nothing extra. No plan fit.',
      headline_other:
        '{{count}} customers wanted under {{ceiling}} a month with nothing extra. No plan fit.',
      headlineFew:
        'Fewer than 5 customers wanted under {{ceiling}} a month with nothing extra. No plan fit.',
      headlineWithoutCeiling_one:
        '{{count}} customer wanted a lower monthly amount with nothing extra. No plan fit.',
      headlineWithoutCeiling_other:
        '{{count}} customers wanted a lower monthly amount with nothing extra. No plan fit.',
      headlineFewWithoutCeiling:
        'Fewer than 5 customers wanted a lower monthly amount with nothing extra. No plan fit.',
      detailHidden:
        'Fewer than 5 customers missed out in this period, so the detail stays hidden to keep their answers private.',
      noInsight: 'No single product had enough missed sales in this period to name it.',
      lowestNoCost: '{{productName}}: the lowest no-cost plan is {{monthly}} a month.',
      leastExtraUnderCeiling:
        'The plan under {{ceiling}} a month with the least extra adds {{extra}} extra in total.',
      noPlanUnderCeiling: 'No plan on this product comes under {{ceiling}} a month.',
      suggestedAction: 'Suggested action',
      askBrand: 'Ask the brand for a {{tenures}}-month no-cost plan on this model.',
    },
    share: {
      button: 'Share with brand rep',
      copied: 'Copied. Paste it in a message to your brand rep.',
      copyByHand: 'Copying is not available on this device. Select this text and copy it.',
      summary:
        '{{shopName}}, {{periodLabel}}: {{customerCount}} customers wanted {{productName}} under {{ceiling}} a month with nothing extra. The lowest no-cost plan is {{lowestMonthly}} a month.',
      request: 'Could you offer a {{tenures}}-month no-cost plan on this model?',
    },
    budgets: {
      title: 'Monthly budgets customers entered ({{total}})',
      hidden:
        'Fewer than 5 customers told a budget in this period, so this chart stays hidden to keep their answers private.',
      hiddenCount: 'Hidden',
      hiddenBucketsNote: 'Some ranges are hidden to keep customers’ answers private.',
      legendUnder: 'Under {{ceiling}}',
      legendFrom: '{{ceiling}} and above',
      rangeUnder: 'Under {{upper}}',
      rangeBetween: '{{lower}} to {{upper}}',
      rangeFrom: '{{lower}} and above',
      noCostPlanTag: 'No-cost {{monthly}}',
      lenderPlanTag: '{{lender}} {{monthly}}',
      columnRange: 'Monthly budget',
      columnCustomers: 'Customers',
      columnPlans: 'Plans in this range',
    },
    moneyDue: {
      title: 'Money due from brands',
      panelLabel: 'Money due from brands detail',
      nextPayment: 'For no-cost EMI sales. Next payment expected {{date}}.',
      nothingDue: 'Nothing is due from brands right now.',
      explainer:
        'On a no-cost EMI sale the customer pays nothing extra, so the brand covers that cost. The brand pays you weeks after the sale, not at the counter. This shows what cash is still to come.',
      noBatches: 'No batches are waiting for payment.',
      batchName_one: 'Batch {{batchNumber}}, {{count}} sale',
      batchName_other: 'Batch {{batchNumber}}, {{count}} sales',
      expected: 'Expected {{date}}',
      status: {
        CLAIM_FILED: 'Claim filed',
        WAITING_FOR_BRAND: 'Waiting for brand',
        NOT_YET_DUE: 'Not yet due',
      },
      datesAreEstimates: 'Dates are estimates from the brands’ offer terms.',
    },
    actions: {
      title: 'What you can do to sell more',
      none: 'Nothing to suggest for this period yet.',
      longerNoCost: {
        title: 'Ask the brand for a longer no-cost plan on the {{productName}}',
        detail: '{{tenures}} months with nothing extra would be {{monthlyAmounts}} a month.',
        missedCustomers_one: '{{count}} customer wanted under {{ceiling}} a month.',
        missedCustomers_other: '{{count}} customers wanted under {{ceiling}} a month.',
        fewMissedCustomers: 'Fewer than 5 customers wanted under {{ceiling}} a month.',
      },
      cheaperModel: {
        title: 'Keep the {{productName}} ready for budget buyers',
        detail_one:
          'At {{price}} it is {{monthly}} a month for {{count}} month with nothing extra.',
        detail_other:
          'At {{price}} it is {{monthly}} a month for {{count}} months with nothing extra.',
      },
    },
  },
} as const;

// Tamil strings of M5, M6 and M7; the compiler checks they have exactly the English keys.
export const SALES_REPORT_TAMIL_TRANSLATIONS: TranslationsMatching<
  typeof SALES_REPORT_ENGLISH_TRANSLATIONS
> = {
  report: {
    title: 'விற்பனை அறிக்கை', // draft: needs native review
    loading: 'விற்பனை அறிக்கை ஏற்றுகிறது…', // draft: needs native review
    fewerThanFive: '5-க்கும் குறைவான', // draft: needs native review
    range: {
      label: 'காலம்', // draft: needs native review
      TODAY: 'இன்று', // draft: needs native review
      THIS_WEEK: 'இந்த வாரம்', // draft: needs native review
      THIS_MONTH: 'இந்த மாதம்', // draft: needs native review
    },
    empty: {
      title: {
        TODAY: 'இன்று இன்னும் EMI விற்பனை இல்லை', // draft: needs native review
        THIS_WEEK: 'இந்த வாரம் இன்னும் EMI விற்பனை இல்லை', // draft: needs native review
        THIS_MONTH: 'இந்த மாதம் இன்னும் EMI விற்பனை இல்லை', // draft: needs native review
      },
      body: 'வாடிக்கையாளர் EMI பற்றிக் கேட்டால் புதிய EMI விற்பனையைத் தொடங்குங்கள். வாடிக்கையாளர்கள் தேர்வை முடிக்கும்போது உங்கள் அறிக்கை நிரம்பும்.', // draft: needs native review
    },
    funnel: {
      title: 'வாடிக்கையாளர்கள் எங்கே விலகுகிறார்கள்', // draft: needs native review
      stage: {
        STARTED: 'தொடங்கினர்', // draft: needs native review
        BUDGET_TOLD: 'பட்ஜெட் சொன்னனர்', // draft: needs native review
        PLANS_VIEWED: 'திட்டங்களைப் பார்த்தனர்', // draft: needs native review
        AGREED: 'திட்டத்தை ஏற்றனர்', // draft: needs native review
        PAID: 'பணம் செலுத்தினர்', // draft: needs native review
      },
      afterStage: {
        STARTED: 'தொடங்கிய', // draft: needs native review
        BUDGET_TOLD: 'பட்ஜெட் சொன்ன', // draft: needs native review
        PLANS_VIEWED: 'திட்டங்களைப் பார்த்த', // draft: needs native review
        AGREED: 'திட்டத்தை ஏற்ற', // draft: needs native review
        PAID: 'பணம் செலுத்திய', // draft: needs native review
      },
      biggestDrop_one: '{{stagePhrase}} பின் {{count}} வாடிக்கையாளர் விலகினார். இதுவே பெரிய சரிவு.', // draft: needs native review
      biggestDrop_other:
        '{{stagePhrase}} பின் {{count}} வாடிக்கையாளர்கள் விலகினர். இதுவே பெரிய சரிவு.', // draft: needs native review
      biggestDropWithoutCount: '{{stagePhrase}} பின் பெரிய சரிவு ஏற்பட்டது.', // draft: needs native review
    },
    missedSales: {
      title: 'தவறிய விற்பனைகள்', // draft: needs native review
      panelLabel: 'தவறிய விற்பனை விவரம்', // draft: needs native review
      none: 'இந்தக் காலத்தில் தவறிய விற்பனை இல்லை.', // draft: needs native review
      headline_one:
        '{{count}} வாடிக்கையாளர் கூடுதல் இல்லாமல் மாதம் {{ceiling}}-க்குள் விரும்பினார். எந்தத் திட்டமும் பொருந்தவில்லை.', // draft: needs native review
      headline_other:
        '{{count}} வாடிக்கையாளர்கள் கூடுதல் இல்லாமல் மாதம் {{ceiling}}-க்குள் விரும்பினர். எந்தத் திட்டமும் பொருந்தவில்லை.', // draft: needs native review
      headlineFew:
        '5-க்கும் குறைவான வாடிக்கையாளர்கள் கூடுதல் இல்லாமல் மாதம் {{ceiling}}-க்குள் விரும்பினர். எந்தத் திட்டமும் பொருந்தவில்லை.', // draft: needs native review
      headlineWithoutCeiling_one:
        '{{count}} வாடிக்கையாளர் கூடுதல் இல்லாமல் குறைந்த மாதத் தொகையை விரும்பினார். எந்தத் திட்டமும் பொருந்தவில்லை.', // draft: needs native review
      headlineWithoutCeiling_other:
        '{{count}} வாடிக்கையாளர்கள் கூடுதல் இல்லாமல் குறைந்த மாதத் தொகையை விரும்பினர். எந்தத் திட்டமும் பொருந்தவில்லை.', // draft: needs native review
      headlineFewWithoutCeiling:
        '5-க்கும் குறைவான வாடிக்கையாளர்கள் கூடுதல் இல்லாமல் குறைந்த மாதத் தொகையை விரும்பினர். எந்தத் திட்டமும் பொருந்தவில்லை.', // draft: needs native review
      detailHidden:
        'இந்தக் காலத்தில் 5-க்கும் குறைவானவர்களே விற்பனையைத் தவறவிட்டதால், அவர்களின் பதில்களைப் பாதுகாக்க விவரம் மறைக்கப்பட்டுள்ளது.', // draft: needs native review
      noInsight: 'இந்தக் காலத்தில் பெயரிடும் அளவுக்குத் தவறிய விற்பனை உள்ள ஒரே பொருள் இல்லை.', // draft: needs native review
      lowestNoCost: '{{productName}}: குறைந்த கட்டணமில்லா திட்டம் மாதம் {{monthly}}.', // draft: needs native review
      leastExtraUnderCeiling:
        'மாதம் {{ceiling}}-க்குள் உள்ள குறைந்த கூடுதல் திட்டம் மொத்தம் {{extra}} கூடுதல் சேர்க்கிறது.', // draft: needs native review
      noPlanUnderCeiling: 'இந்தப் பொருளில் மாதம் {{ceiling}}-க்குள் எந்தத் திட்டமும் இல்லை.', // draft: needs native review
      suggestedAction: 'பரிந்துரைக்கும் செயல்', // draft: needs native review
      askBrand: 'இந்த மாடலுக்கு {{tenures}} மாத கட்டணமில்லா திட்டத்தை பிராண்டிடம் கேளுங்கள்.', // draft: needs native review
    },
    share: {
      button: 'பிராண்ட் பிரதிநிதியுடன் பகிர்', // draft: needs native review
      copied: 'நகலெடுக்கப்பட்டது. உங்கள் பிராண்ட் பிரதிநிதிக்கான செய்தியில் ஒட்டுங்கள்.', // draft: needs native review
      copyByHand:
        'இந்தச் சாதனத்தில் நகலெடுக்க முடியவில்லை. இந்த உரையைத் தேர்ந்தெடுத்து நகலெடுக்கவும்.', // draft: needs native review
      summary:
        '{{shopName}}, {{periodLabel}}: {{customerCount}} வாடிக்கையாளர்கள் {{productName}}-ஐக் கூடுதல் இல்லாமல் மாதம் {{ceiling}}-க்குள் விரும்பினர். குறைந்த கட்டணமில்லா திட்டம் மாதம் {{lowestMonthly}}.', // draft: needs native review
      request: 'இந்த மாடலுக்கு {{tenures}} மாத கட்டணமில்லா திட்டம் வழங்க முடியுமா?', // draft: needs native review
    },
    budgets: {
      title: 'வாடிக்கையாளர்கள் சொன்ன மாதாந்திர பட்ஜெட் ({{total}})', // draft: needs native review
      hidden:
        'இந்தக் காலத்தில் 5-க்கும் குறைவானவர்களே பட்ஜெட் சொன்னதால், அவர்களின் பதில்களைப் பாதுகாக்க இந்த வரைபடம் மறைக்கப்பட்டுள்ளது.', // draft: needs native review
      hiddenCount: 'மறைக்கப்பட்டது', // draft: needs native review
      hiddenBucketsNote: 'வாடிக்கையாளர்களின் பதில்களைப் பாதுகாக்க சில வரம்புகள் மறைக்கப்பட்டுள்ளன.', // draft: needs native review
      legendUnder: '{{ceiling}}-க்குக் கீழ்', // draft: needs native review
      legendFrom: '{{ceiling}} மற்றும் அதற்கு மேல்', // draft: needs native review
      rangeUnder: '{{upper}}-க்குக் கீழ்', // draft: needs native review
      rangeBetween: '{{lower}} முதல் {{upper}} வரை', // draft: needs native review
      rangeFrom: '{{lower}} மற்றும் அதற்கு மேல்', // draft: needs native review
      noCostPlanTag: 'கட்டணமில்லா {{monthly}}', // draft: needs native review
      lenderPlanTag: '{{lender}} {{monthly}}', // draft: needs native review
      columnRange: 'மாதாந்திர பட்ஜெட்', // draft: needs native review
      columnCustomers: 'வாடிக்கையாளர்கள்', // draft: needs native review
      columnPlans: 'இந்த வரம்பில் உள்ள திட்டங்கள்', // draft: needs native review
    },
    moneyDue: {
      title: 'பிராண்டுகளிடமிருந்து வர வேண்டிய பணம்', // draft: needs native review
      panelLabel: 'பிராண்டுகளிடமிருந்து வர வேண்டிய பண விவரம்', // draft: needs native review
      nextPayment:
        'கட்டணமில்லா EMI விற்பனைகளுக்கு. அடுத்த தொகை {{date}} அன்று எதிர்பார்க்கப்படுகிறது.', // draft: needs native review
      nothingDue: 'இப்போது பிராண்டுகளிடமிருந்து வர வேண்டியது எதுவும் இல்லை.', // draft: needs native review
      explainer:
        'கட்டணமில்லா EMI விற்பனையில் வாடிக்கையாளர் கூடுதலாக எதுவும் செலுத்துவதில்லை; அந்தச் செலவை பிராண்ட் ஏற்கிறது. பிராண்ட் உங்களுக்கு விற்பனைக்குச் சில வாரங்கள் கழித்துப் பணம் தரும், கவுண்டரில் அல்ல. இன்னும் வர வேண்டிய பணத்தை இது காட்டுகிறது.', // draft: needs native review
      noBatches: 'பணத்திற்காகக் காத்திருக்கும் தொகுப்புகள் இல்லை.', // draft: needs native review
      batchName_one: 'தொகுப்பு {{batchNumber}}, {{count}} விற்பனை', // draft: needs native review
      batchName_other: 'தொகுப்பு {{batchNumber}}, {{count}} விற்பனைகள்', // draft: needs native review
      expected: 'எதிர்பார்ப்பு {{date}}', // draft: needs native review
      status: {
        CLAIM_FILED: 'கோரிக்கை பதிவாகியது', // draft: needs native review
        WAITING_FOR_BRAND: 'பிராண்டுக்காகக் காத்திருக்கிறது', // draft: needs native review
        NOT_YET_DUE: 'இன்னும் நாள் வரவில்லை', // draft: needs native review
      },
      datesAreEstimates: 'தேதிகள் பிராண்டுகளின் சலுகை விதிமுறைகளின்படி மதிப்பீடுகள்.', // draft: needs native review
    },
    actions: {
      title: 'மேலும் விற்க நீங்கள் செய்யக்கூடியவை', // draft: needs native review
      none: 'இந்தக் காலத்திற்கு இன்னும் பரிந்துரை இல்லை.', // draft: needs native review
      longerNoCost: {
        title: '{{productName}}-க்கு நீண்ட கட்டணமில்லா திட்டத்தை பிராண்டிடம் கேளுங்கள்', // draft: needs native review
        detail: 'கூடுதல் இல்லாமல் {{tenures}} மாதங்கள் என்றால் மாதம் {{monthlyAmounts}} ஆகும்.', // draft: needs native review
        missedCustomers_one: '{{count}} வாடிக்கையாளர் மாதம் {{ceiling}}-க்குள் விரும்பினார்.', // draft: needs native review
        missedCustomers_other: '{{count}} வாடிக்கையாளர்கள் மாதம் {{ceiling}}-க்குள் விரும்பினர்.', // draft: needs native review
        fewMissedCustomers:
          '5-க்கும் குறைவான வாடிக்கையாளர்கள் மாதம் {{ceiling}}-க்குள் விரும்பினர்.', // draft: needs native review
      },
      cheaperModel: {
        title: 'பட்ஜெட் வாங்குபவர்களுக்காக {{productName}}-ஐத் தயாராக வையுங்கள்', // draft: needs native review
        detail_one: '{{price}} விலையில் கூடுதல் இல்லாமல் {{count}} மாதத்திற்கு மாதம் {{monthly}}.', // draft: needs native review
        detail_other:
          '{{price}} விலையில் கூடுதல் இல்லாமல் {{count}} மாதங்களுக்கு மாதம் {{monthly}}.', // draft: needs native review
      },
    },
  },
};
