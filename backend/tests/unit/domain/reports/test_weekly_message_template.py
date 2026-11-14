"""WeeklyMessageTemplate: the design week in English and Tamil, and sentences left out safely."""

from dataclasses import replace
from datetime import date
from zoneinfo import ZoneInfo

from emi_copilot.core.indian_rupee_formatter import format_paise_as_whole_rupees
from emi_copilot.domain.funnel import FunnelStage
from emi_copilot.domain.reports.budget_buckets import build_budget_bucket_report
from emi_copilot.domain.reports.funnel_report import FunnelReport
from emi_copilot.domain.reports.missed_sales import MissedSalesAnalysis, MissedSalesReport
from emi_copilot.domain.reports.money_due_report import MoneyDueReport
from emi_copilot.domain.reports.reporting_period import ReportingPeriod
from emi_copilot.domain.reports.small_count_suppression import SmallCountSuppressionPolicy
from emi_copilot.domain.reports.suggested_actions import SuggestionContext, suggest_actions
from emi_copilot.domain.reports.weekly_message_template import (
    WeeklyMessageFacts,
    WeeklyMessageTemplate,
    WeeklyMessageText,
)
from emi_copilot.domain.reports.weekly_message_wording import (
    ENGLISH_WORDING,
    TAMIL_WORDING,
    MessageLanguage,
)
from tests.report_builders import (
    build_design_missed_sales_analysis,
    build_design_settlement_batches,
)

INDIA = ZoneInfo("Asia/Kolkata")
POLICY = SmallCountSuppressionPolicy()
DESIGN_COUNTS = {
    FunnelStage.STARTED: 120,
    FunnelStage.BUDGET_TOLD: 96,
    FunnelStage.PLANS_VIEWED: 88,
    FunnelStage.AGREED: 51,
    FunnelStage.PAID: 44,
}
TEMPLATE = WeeklyMessageTemplate(format_paise_as_whole_rupees)


def _missed_sales_report(analysis: MissedSalesAnalysis) -> MissedSalesReport:
    """Builds the missed-sales card of an analysis with empty buckets."""
    return MissedSalesReport.from_analysis(
        analysis,
        build_budget_bucket_report((0, 0, 0, 0, 0), None, (), POLICY, cohort_sale_count=0),
        POLICY,
    )


def build_design_facts() -> WeeklyMessageFacts:
    """The design week of 9 to 15 November 2026 with every DESIGN_SPEC number."""
    analysis = build_design_missed_sales_analysis()
    return WeeklyMessageFacts(
        period=ReportingPeriod.week_starting(date(2026, 11, 9), INDIA),
        funnel=FunnelReport.from_stage_counts(DESIGN_COUNTS, POLICY),
        missed_sales=_missed_sales_report(analysis),
        money_due=MoneyDueReport.from_batches(build_design_settlement_batches()),
        suggested_actions=suggest_actions(SuggestionContext(analysis, POLICY)),
    )


def test_design_week_in_english_uses_the_computed_numbers_and_no_most_claim() -> None:
    """M8 with plan Q9's corrections: the biggest drop, and ₹2,444 or ₹1,833 instead of "near"."""
    assert TEMPLATE.render(build_design_facts()).english == WeeklyMessageText(
        title="Your EMI sales, 9 to 15 November",
        paragraphs=(
            "44 of 120 customers bought on EMI. The biggest drop was after seeing the plans.",
            "12 customers wanted under ₹3,000 a month with nothing extra, and no plan fit. "
            "₹1,84,000 is due from brands, first payment around 13 Jan.",
            "One thing to do: ask the brand for a 9 or 12-month no-cost plan on Example phone, "
            "128 GB. That would be ₹2,444 or ₹1,833 a month.",
        ),
    )


def test_design_week_in_tamil_reuses_the_mockup_wording_with_the_same_numbers() -> None:
    """The Tamil text carries exactly the English numbers (draft wording)."""
    assert TEMPLATE.render(build_design_facts()).tamil == WeeklyMessageText(
        title="உங்கள் EMI விற்பனை, 9 முதல் 15 நவம்பர்",
        paragraphs=(
            "120 வாடிக்கையாளர்களில் 44 பேர் EMI-யில் வாங்கினர். திட்டங்களைப் பார்த்த பின் அதிகம் பேர் விலகினர்.",
            "12 பேர் கூடுதல் இல்லாமல் மாதம் ₹3,000-க்குள் விரும்பினர், எந்தத் திட்டமும் "
            "பொருந்தவில்லை. பிராண்டுகளிடமிருந்து ₹1,84,000 வர வேண்டும், முதல் தொகை சுமார் "
            "13 ஜனவரி.",
            "செய்ய வேண்டியது: Example phone, 128 GB-க்கு 9 அல்லது 12 மாத கட்டணமில்லா "
            "திட்டத்தை பிராண்டிடம் கேளுங்கள். அது மாதம் ₹2,444 அல்லது ₹1,833 ஆகும்.",
        ),
    )


def test_suppressed_numbers_leave_their_sentences_out() -> None:
    """3 paid and 3 missed are "fewer than 5", so neither sentence is written.

    With 3 paid of 51 agreed, the biggest drop moves to after agreeing; it sits beside the hidden
    paid count, so the report omits it and its sentence is left out.
    """
    small_counts = {**DESIGN_COUNTS, FunnelStage.PAID: 3}
    phone_128_gb, *other_products = build_design_missed_sales_analysis().products_missed_sales
    analysis = MissedSalesAnalysis.from_products(
        [replace(phone_128_gb, tally=replace(phone_128_gb.tally, missed_count=3)), *other_products]
    )
    facts = replace(
        build_design_facts(),
        funnel=FunnelReport.from_stage_counts(small_counts, POLICY),
        missed_sales=_missed_sales_report(analysis),
    )
    english = TEMPLATE.render_in(MessageLanguage.ENGLISH, facts)
    assert facts.funnel.biggest_drop is None
    assert english.paragraphs[0] == "₹1,84,000 is due from brands, first payment around 13 Jan."
    assert "biggest drop" not in " ".join(english.paragraphs)
    assert "3" not in english.paragraphs[0].replace("13 Jan", "")


def test_a_suppressed_missed_count_leaves_the_action_sentence_out_too() -> None:
    """Every action comes from the missed sales; with 3 missed, none is said, even if given."""
    phone_128_gb, *other_products = build_design_missed_sales_analysis().products_missed_sales
    analysis = MissedSalesAnalysis.from_products(
        [replace(phone_128_gb, tally=replace(phone_128_gb.tally, missed_count=3)), *other_products]
    )
    facts = replace(build_design_facts(), missed_sales=_missed_sales_report(analysis))
    assert facts.suggested_actions
    for language in MessageLanguage:
        paragraphs = TEMPLATE.render_in(language, facts).paragraphs
        assert len(paragraphs) == 2
        assert "₹2,444" not in " ".join(paragraphs)


def test_a_suppressed_drop_and_no_money_due_or_action_leave_only_the_sales_sentence() -> None:
    """A drop of 3 is not described; nothing due and no action leave no second or third part."""
    counts = dict.fromkeys(DESIGN_COUNTS, 9) | {FunnelStage.PAID: 6}
    facts = replace(
        build_design_facts(),
        funnel=FunnelReport.from_stage_counts(counts, POLICY),
        missed_sales=_missed_sales_report(MissedSalesAnalysis.from_products([])),
        money_due=MoneyDueReport.from_batches(()),
        suggested_actions=(),
    )
    assert TEMPLATE.render_in(MessageLanguage.ENGLISH, facts).paragraphs == (
        "6 of 9 customers bought on EMI.",
    )


def test_a_week_without_sales_says_so_in_both_languages() -> None:
    """The empty shop: one plain sentence, no zeros to read."""
    facts = replace(
        build_design_facts(),
        funnel=FunnelReport.from_stage_counts({}, POLICY),
        missed_sales=_missed_sales_report(MissedSalesAnalysis.from_products([])),
        money_due=MoneyDueReport.from_batches(()),
        suggested_actions=(),
    )
    messages = TEMPLATE.render(facts)
    assert messages.english.paragraphs == (ENGLISH_WORDING.no_sales_yet,)
    assert messages.tamil.paragraphs == (TAMIL_WORDING.no_sales_yet,)


def test_a_week_across_two_months_names_both_months() -> None:
    """30 November to 6 December."""
    facts = replace(
        build_design_facts(), period=ReportingPeriod.week_starting(date(2026, 11, 30), INDIA)
    )
    messages = TEMPLATE.render(facts)
    assert messages.english.title == "Your EMI sales, 30 November to 6 December"
    assert messages.tamil.title == "உங்கள் EMI விற்பனை, 30 நவம்பர் முதல் 6 டிசம்பர்"


def test_a_cheaper_model_as_the_only_action_is_described_with_its_figures() -> None:
    """M5's second tip: ₹18,000, ₹3,000 a month for 6 months."""
    facts = build_design_facts()
    facts = replace(facts, suggested_actions=facts.suggested_actions[1:])
    assert TEMPLATE.render_in(MessageLanguage.ENGLISH, facts).paragraphs[2] == (
        "One thing to do: keep Example phone, 64 GB ready for budget buyers. At ₹18,000 it is "
        "₹3,000 a month for 6 months with nothing extra."
    )
    assert "₹18,000" in TEMPLATE.render_in(MessageLanguage.TAMIL, facts).paragraphs[2]


def test_every_funnel_stage_but_paid_has_a_biggest_drop_sentence_in_both_languages() -> None:
    """A drop is always after an earlier stage, so PAID never needs a sentence."""
    stages_with_drop_sentence = set(FunnelStage) - {FunnelStage.PAID}
    assert set(ENGLISH_WORDING.biggest_drop_after_stage) == stages_with_drop_sentence
    assert set(TAMIL_WORDING.biggest_drop_after_stage) == stages_with_drop_sentence


def test_the_message_never_uses_urgency_or_best_wording() -> None:
    """Plain wording rule (CLAUDE.md rule 7)."""
    english_text = " ".join(TEMPLATE.render(build_design_facts()).english.paragraphs).lower()
    for banned_word in ("best", "hurry", "now", "approved", "declined", "most who"):
        assert banned_word not in english_text
